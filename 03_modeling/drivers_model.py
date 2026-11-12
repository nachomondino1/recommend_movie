"""
CRISP-DM · Modelado (versión "qué hace que una película tenga buena nota").

Sin tus notas de IMDb: se usa todo el catálogo de TMDB (miles de títulos) y la respuesta es la nota pública de TMDB.
Aprendizaje supervisado, regresión. La pregunta no es "qué nota le pondré yo" sino "qué variables se asocian con
una nota más alta o más baja". Se miran tres cosas, siempre fuera de muestra:

  1. Qué tan bien se puede predecir la nota (R² y error medio contra predecir siempre el promedio).
  2. Qué grupo de variables pesa más: al mezclar al azar un grupo en datos no vistos, cuánto cae el R² (importancia
     por permutación) y cuánto cae si el modelo nunca lo ve (ablación).
  3. Efectos ajustados por género, formato, año y duración (regresión lineal con bootstrap).

Más pruebas de robustez: otros umbrales de votos, solo películas, solo series, y la versión que sí usa popularidad y
votos (círculo vicioso: dependen de la nota, así que se muestra aparte).

    python 03_modeling/drivers_model.py     # escribe data/03_modeling/drivers_results.json
"""

import sys
import warnings
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]

import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, RepeatedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import TargetEncoder

from config import MODELING_DIR, PREP_DIR

warnings.filterwarnings("ignore")
SEED = 7
MIN_VOTES = 100          # por debajo de esto la nota de TMDB es muy ruidosa
OUT = MODELING_DIR / "drivers_results.json"


# --------------------------------------------------------------------------- #
# Variables y grupos
# --------------------------------------------------------------------------- #
def groups_of(cols) -> dict:
    cols = list(cols)
    return {
        "Formato (serie o película)": ["is_tv", "seasons"],
        "Duración": ["runtime", "runtime_missing"],
        "Año de estreno": ["year"],
        "Géneros": [c for c in cols if c.startswith("g_")] + ["n_genres"],
        "Director": ["director", "director_n_titles", "has_director", "n_directors"],
        "Plataformas": [c for c in cols if c.startswith("p_")] + ["n_providers"],
        "Sinopsis (largo)": ["overview_len", "has_overview"],
    }


CIRCULAR = {"Popularidad y votos (circular)": ["log_popularity", "log_votes"]}


def load(min_votes: int = MIN_VOTES, media: str | None = None) -> pd.DataFrame:
    df = pd.read_csv(PREP_DIR / "titles_features.csv")
    df = df[(df["votes"] >= min_votes) & df["rating"].notna()]
    if media:
        df = df[df["media_type"] == media]
    df = df.reset_index(drop=True)
    df["overview"] = df["overview"].fillna("")
    df["log_popularity"] = np.log1p(df["popularity"])
    df["log_votes"] = np.log10(df["votes"])
    return df


def pipeline(cols) -> Pipeline:
    """HistGradientBoosting + el director como promedio de nota de sus otros títulos (codificado dentro de cada
    fold de entrenamiento, para que la nota del título a predecir no se cuele)."""
    te = [c for c in ["director"] if c in cols]
    rest = [c for c in cols if c not in te]
    pre = ColumnTransformer([("dir", TargetEncoder(target_type="continuous", cv=5, random_state=SEED), te)] if te else [],
                            remainder="passthrough")
    return Pipeline([("pre", pre), ("m", HistGradientBoostingRegressor(max_iter=250, learning_rate=0.06, random_state=SEED))])


# --------------------------------------------------------------------------- #
# 1. Qué tan bien se predice
# --------------------------------------------------------------------------- #
def cv_scores(df, cols, n_repeats=2):
    y = df["rating"].to_numpy()
    r2s, maes = [], []
    for tr, te in RepeatedKFold(n_splits=5, n_repeats=n_repeats, random_state=SEED).split(df):
        m = pipeline(cols).fit(df.iloc[tr][cols], y[tr])
        p = m.predict(df.iloc[te][cols])
        r2s.append(r2_score(y[te], p)); maes.append(mean_absolute_error(y[te], p))
    base_mae = np.mean([np.abs(y[te] - y[tr].mean()).mean() for tr, te in KFold(5, shuffle=True, random_state=SEED).split(df)])
    return {"r2": float(np.mean(r2s)), "r2_sd": float(np.std(r2s)), "mae": float(np.mean(maes)), "mae_base": float(base_mae)}


# --------------------------------------------------------------------------- #
# 2. Qué grupo pesa más
# --------------------------------------------------------------------------- #
def importance_and_ablation(df, groups, n_perm=5):
    cols = [c for cs in groups.values() for c in cs]
    y = df["rating"].to_numpy()
    rng = np.random.default_rng(SEED)
    drops = {g: [] for g in groups}
    for tr, te in RepeatedKFold(n_splits=5, n_repeats=2, random_state=SEED).split(df):
        m = pipeline(cols).fit(df.iloc[tr][cols], y[tr])
        Xte, yte = df.iloc[te][cols].copy(), y[te]
        base = r2_score(yte, m.predict(Xte))
        for g, cs in groups.items():
            for _ in range(n_perm):
                Xp = Xte.copy()
                Xp[cs] = Xte[cs].iloc[rng.permutation(len(Xte))].to_numpy()   # se mezclan juntas, para no romper el grupo
                drops[g].append(base - r2_score(yte, m.predict(Xp)))
    full = cv_scores(df, cols)["r2"]
    out = []
    for g, cs in groups.items():
        without = [c for c in cols if c not in cs]
        out.append({"group": g, "perm_drop": float(np.mean(drops[g])), "perm_sd": float(np.std(drops[g])),
                    "r2_without": cv_scores(df, without, 1)["r2"]})
    for o in out:
        o["ablation_drop"] = float(full - o["r2_without"])
    return sorted(out, key=lambda o: -o["perm_drop"]), float(full)


# --------------------------------------------------------------------------- #
# 3. Efectos ajustados (en puntos de nota)
# --------------------------------------------------------------------------- #
def adjusted_effects(df, n_boot=300):
    gcols = [c for c in df.columns if c.startswith("g_")]
    X = df[gcols + ["is_tv"]].copy()
    X["decada"] = (df["year"].fillna(df["year"].median()) - 2000) / 10           # por década, centrado en 2000
    X["hora_extra"] = (df["runtime"].fillna(df["runtime"].median()) - 100) / 60     # por hora de duración sobre 100 min
    X["director_prolifico"] = (df["director_n_titles"] >= 3).astype(int)
    y = df["rating"].to_numpy()
    base = Ridge(alpha=1.0).fit(X, y).coef_
    rng = np.random.default_rng(SEED)
    boots = np.array([Ridge(alpha=1.0).fit(X.iloc[i], y[i]).coef_ for i in (rng.integers(0, len(X), len(X)) for _ in range(n_boot))])
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    names = {"is_tv": "Es serie (contra película)", "decada": "Cada década más reciente", "hora_extra": "Cada hora más de duración",
             "director_prolifico": "Director con 3+ títulos en el catálogo"}
    rows = [{"var": names.get(c, c[2:] if c.startswith("g_") else c), "kind": "gen" if c.startswith("g_") else "otro",
             "effect": float(b), "lo": float(l), "hi": float(h), "n": int(df[c].sum()) if c in df and c.startswith("g_") else None}
            for c, b, l, h in zip(X.columns, base, lo, hi)]
    return sorted(rows, key=lambda r: -abs(r["effect"]))


def raw_by_genre(df):
    gcols = [c for c in df.columns if c.startswith("g_")]
    return sorted([{"genre": c[2:], "mean": float(df.loc[df[c] == 1, "rating"].mean()), "n": int(df[c].sum())} for c in gcols],
                  key=lambda r: -r["mean"])


def words(df, top=14):
    """Palabras de la sinopsis asociadas a notas más altas o más bajas (regresión sobre TF-IDF)."""
    tf = TfidfVectorizer(min_df=60, max_df=0.4, ngram_range=(1, 1), strip_accents=None)
    X = tf.fit_transform(df["overview"])
    r = Ridge(alpha=8.0).fit(X, df["rating"] - df["rating"].mean())
    order = np.argsort(r.coef_); vocab = np.array(tf.get_feature_names_out())
    return {"pos": [(w, float(r.coef_[i])) for w, i in zip(vocab[order[::-1][:top]], order[::-1][:top])],
            "neg": [(w, float(r.coef_[i])) for w, i in zip(vocab[order[:top]], order[:top])], "vocab": int(len(vocab))}


def main():
    df = load()
    groups = groups_of(df.columns)
    cols = [c for cs in groups.values() for c in cs]
    res = {"n": int(len(df)), "min_votes": MIN_VOTES, "n_movies": int((df.is_tv == 0).sum()), "n_tv": int(df.is_tv.sum()),
           "rating_mean": float(df.rating.mean()), "rating_sd": float(df.rating.std()), "share_ge7": float((df.rating >= 7).mean())}
    print(f"n={res['n']}  nota media {res['rating_mean']:.2f}  sd {res['rating_sd']:.2f}")

    res["performance"] = {"contenido": cv_scores(df, cols)}
    res["performance"]["contenido + popularidad y votos"] = cv_scores(df, cols + CIRCULAR["Popularidad y votos (circular)"])
    for k, v in res["performance"].items():
        print(f"  {k:35s} R²={v['r2']:.3f} ±{v['r2_sd']:.3f}  error medio {v['mae']:.3f} (promedio: {v['mae_base']:.3f})")

    res["importance"], res["full_r2"] = importance_and_ablation(df, groups)
    print("\nImportancia por grupo (caída de R²):")
    for o in res["importance"]:
        print(f"  {o['group']:30s} permutación {o['perm_drop']:+.3f} ±{o['perm_sd']:.3f}   sin el grupo {o['ablation_drop']:+.3f}")

    res["effects"] = adjusted_effects(df)
    res["raw_by_genre"] = raw_by_genre(df)
    res["words"] = words(df)
    print("\nEfectos ajustados (puntos de nota, IC 95 %):")
    for r in res["effects"][:12]:
        print(f"  {r['var']:42s} {r['effect']:+.2f}  [{r['lo']:+.2f}, {r['hi']:+.2f}]")

    # robustez
    rob = []
    for label, kw in [("Votos ≥ 50", dict(min_votes=50)), ("Votos ≥ 300", dict(min_votes=300)), ("Votos ≥ 1.000", dict(min_votes=1000)),
                      ("Solo películas", dict(media="movie")), ("Solo series", dict(media="tv"))]:
        d = load(**kw)
        g = {k: [c for c in v if c in d.columns] for k, v in groups_of(d.columns).items()}
        if kw.get("media"):
            g.pop("Formato (serie o película)", None)
        cs = [c for v in g.values() for c in v]
        s = cv_scores(d, cs, 1)
        rob.append({"label": label, "n": int(len(d)), **s})
        print(f"  robustez · {label:16s} n={len(d):5d}  R²={s['r2']:.3f}  error {s['mae']:.3f} (promedio {s['mae_base']:.3f})")
    res["robustness"] = rob
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"\nGuardado: {OUT}")


if __name__ == "__main__":
    main()
