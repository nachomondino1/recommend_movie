"""
CRISP-DM · Modelado · 3/3 «Assess model» (comparar resultados y decidir qué modelo sirve).

Todo lo que mira resultados, con las reglas de test_design.py y los modelos de build_model.py:

  Comparación estándar (`make eval`)
    - compare_models()         : regresión y binario contra las bases, con una CV de 5 folds
    - learning_curve_report()  : cómo mejora el modelo al sumar títulos
    - plot_history()           : trayectoria REAL de los scores según creció ratings.csv
    - review_insights()        : palabras de tus reseñas (un insight para vos, no entra al modelo)

  Prueba de robustez (`make robust`, ~80 s): ¿algún modelo le gana de verdad a la nota de IMDb?
    CV repetida, 9 modelos contra la nota de IMDb CALIBRADA, bootstrap pareado con IC 95 %, control
    de permutación, poder estadístico y curva de aprendizaje con bandas de error. Resultados y lectura
    en 04_evaluation/evaluation.md.

    python 03_modeling/assess_model.py            # comparación estándar
    python 03_modeling/assess_model.py --robust   # además, la prueba de robustez
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import argparse
import re
import warnings
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import KFold, cross_val_predict, learning_curve
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from build_model import build_classifier, build_regressor, make_preprocessor
from config import METRICS_CSV, MODELING_DIR
from features import build, feature_groups
from test_design import (LIKE_THRESHOLD, N_BOOT, ROBUST_REPEATS, ROBUST_SEED, calibrate_imdb, ci95,
                         classification_cv, like_labels, paired_bootstrap, regression_cv, score_predictions)
from prepare_tmdb import load_reviews

warnings.filterwarnings("ignore")


# =========================================================================== #
# A. Comparación estándar
# =========================================================================== #
# --------------------------------------------------------------------------- #
# Diagnósticos
# --------------------------------------------------------------------------- #
def compare_models() -> None:
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    kf = regression_cv()

    rows = []

    def rec(name, pred):
        err = np.abs(pred - y)
        rows.append({"modelo": name, "MAE": err.mean(),
                     "RMSE": np.sqrt(((pred - y) ** 2).mean()), "±1": (err <= 1).mean()})

    rec("Baseline: media de tu nota", np.full(len(y), y.mean()))
    rec("Regla fija: IMDb + media(desvío)", imdb + resid.mean())
    for name, est in {"Ridge (nota directa)": Ridge(alpha=3.0),
                      "RandomForest (nota directa)": RandomForestRegressor(400, random_state=42)}.items():
        rec(name, cross_val_predict(Pipeline([("pre", make_preprocessor(groups, "continuous")),
                                              ("m", est)]), X, y, cv=kf))
    for name, est in {"Ridge (desvío)": Ridge(alpha=3.0),
                      "RandomForest (desvío)": RandomForestRegressor(400, random_state=42)}.items():
        pr = cross_val_predict(Pipeline([("pre", make_preprocessor(groups, "continuous")),
                                         ("m", est)]), X, resid, cv=kf)
        rec(name, imdb + pr)
    print("\n--- REGRESIÓN ---")
    print(pd.DataFrame(rows).set_index("modelo").round(3).to_string())

    like = (y >= LIKE_THRESHOLD).astype(int)
    skf = classification_cv()
    brows = []
    for name, est in {"Baseline": DummyClassifier(strategy="most_frequent"),
                      "LogReg": LogisticRegression(C=0.3, max_iter=2000, class_weight="balanced"),
                      "GradientBoosting": GradientBoostingClassifier(random_state=42)}.items():
        pipe = Pipeline([("pre", make_preprocessor(groups, "binary")), ("m", est)])
        pred = cross_val_predict(pipe, X, like, cv=skf)
        proba = cross_val_predict(pipe, X, like, cv=skf, method="predict_proba")[:, 1]
        brows.append({"modelo": name, "accuracy": (pred == like).mean(),
                      "balanced_acc": balanced_accuracy_score(like, pred),
                      "roc_auc": roc_auc_score(like, proba)})
    print(f"\n--- BINARIO (>= {LIKE_THRESHOLD})  positivos {like.sum()}/{len(like)} "
          f"({like.mean():.0%}) ---")
    print(pd.DataFrame(brows).set_index("modelo").round(3).to_string())


def learning_curve_report() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = (y >= LIKE_THRESHOLD).astype(int)
    sizes = np.linspace(0.25, 1.0, 8)

    n1, _, te1 = learning_curve(build_regressor(groups), X, resid, train_sizes=sizes, cv=5,
                                scoring="neg_mean_absolute_error", shuffle=True, random_state=42)
    n2, _, te2 = learning_curve(build_classifier(groups), X, like, train_sizes=sizes,
                                cv=classification_cv(),
                                scoring="roc_auc", shuffle=True, random_state=42)
    mae, auc = -te1.mean(axis=1), te2.mean(axis=1)

    print("\n--- CURVA DE APRENDIZAJE ---")
    print("  n  | MAE  | AUC")
    for a, m, u in zip(n1, mae, auc):
        print(f"  {a:3d} | {m:.3f} | {u:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(n1, mae, "o-", color="tab:red"); ax1.axhline(1.31, ls="--", color="gray")
    ax1.set(title="MAE de la nota vs n entrenamiento", xlabel="n", ylabel="MAE (CV)")
    ax2.plot(n2, auc, "o-", color="tab:blue"); ax2.axhline(0.5, ls="--", color="gray")
    ax2.axhline(0.65, ls=":", color="green")
    ax2.set(title="ROC AUC (>=7) vs n entrenamiento", xlabel="n", ylabel="AUC (CV)")
    fig.tight_layout()
    fig.savefig(MODELING_DIR / "learning_curve.png", dpi=120)
    print(f"Gráfico: {MODELING_DIR / 'learning_curve.png'}")


def plot_history() -> None:
    """Trayectoria REAL de los scores CV según fue creciendo ratings.csv
    (metrics_history.csv). Distinta de la curva de aprendizaje, que es simulada."""
    if not METRICS_CSV.exists():
        return
    hist = pd.read_csv(METRICS_CSV)
    if len(hist) < 2:
        print(f"\n(metrics_history.csv tiene {len(hist)} punto; hacen falta ≥2 para el gráfico)")
        return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax2 = ax1.twinx()
    ax1.plot(hist["n_train"], hist["cv_mae_rating"], "o-", color="tab:red", label="MAE")
    ax2.plot(hist["n_train"], hist["cv_roc_auc_like"], "s-", color="tab:blue", label="AUC")
    ax1.set(xlabel="ratings en el dataset", ylabel="MAE (CV)", title="Trayectoria real de los scores")
    ax2.set_ylabel("ROC AUC (CV)")
    ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(MODELING_DIR / "metrics_history.png", dpi=120)
    print(f"\n--- TRAYECTORIA REAL ({len(hist)} puntos) ---")
    print(hist.to_string(index=False))
    print(f"Gráfico: {MODELING_DIR / 'metrics_history.png'}")


# Spanish stopwords para el análisis de reseñas -- no exhaustivo, alcanza para
# filtrar conectores comunes de un texto corto e informal.
_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero",
    "sus", "le", "ya", "este", "porque", "esta", "entre", "cuando", "muy",
    "sin", "sobre", "también", "hasta", "hay", "donde", "quien", "desde",
    "todo", "nos", "durante", "todos", "uno", "les", "esa", "eso", "ese",
    "ante", "ellos", "esto", "antes", "algunos", "unos", "otro", "otras",
    "otra", "tanto", "estos", "mucho", "quienes", "nada", "muchos", "cual",
    "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "ellas",
    "esos", "esas", "estoy", "estás", "está", "estamos", "están", "tiene",
    "tienen", "hace", "hacer", "había", "soy", "eres", "así", "cada", "vez",
    "bien", "mal", "creo", "pienso", "capitulos", "capítulos", "personaje",
    "mucha", "muchas", "cosas", "cosa",
}


def _review_words(text: str) -> list[str]:
    tokens = re.findall(r"[a-zñáéíóúü]+", str(text).lower())
    return [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]


def review_insights() -> None:
    """Analiza data/01_data_understanding/imdb/reviews.csv: qué palabras aparecen más en la parte 'me gustó'
    vs 'no me gustó', juntando todas tus reseñas. Es un insight para vos -- NO
    entra como feature del modelo, porque no existe reseña para un título que
    todavía no viste."""
    reviews = load_reviews()
    if reviews.empty:
        print("\n(sin reseñas en data/01_data_understanding/imdb/reviews.csv)")
        return

    liked = reviews["Liked"].dropna()
    disliked = reviews["Disliked"].dropna()
    print(f"\n--- RESEÑAS ({len(reviews)} títulos reseñados; {len(liked)} con sección "
          f"'me gustó', {len(disliked)} con 'no me gustó') ---")

    liked_words = Counter(w for t in liked for w in _review_words(t))
    disliked_words = Counter(w for t in disliked for w in _review_words(t))
    if not liked_words and not disliked_words:
        print("Todavía no hay suficiente texto en las reseñas para analizar.")
        return

    print("\nTop palabras en lo que te gustó:")
    for w, c in liked_words.most_common(10):
        print(f"  {w:20s} {c}")
    print("\nTop palabras en lo que NO te gustó:")
    for w, c in disliked_words.most_common(10):
        print(f"  {w:20s} {c}")


# =========================================================================== #
# B. Prueba de robustez: ¿algún modelo le gana de verdad a la nota de IMDb?
# =========================================================================== #
# --------------------------------------------------------------------------- #
# Candidatos: cada uno es fit_predict(Xtr, ytr, Xte) -> nota predicha
# --------------------------------------------------------------------------- #
def _imdb(X) -> np.ndarray:
    return X["IMDb Rating"].to_numpy(dtype=float)


def mean_model(Xtr, ytr, Xte):
    return np.full(len(Xte), ytr.mean())


def imdb_raw(Xtr, ytr, Xte):
    return _imdb(Xte)


def imdb_calibrated(Xtr, ytr, Xte):
    """La base JUSTA (ver test_design.calibrate_imdb): IMDb reescalada a tu forma de puntuar."""
    return calibrate_imdb(_imdb(Xtr), ytr, _imdb(Xte))


def _deviation_model(make_pre, estimator):
    """Predice el desvío (tu nota - IMDb calibrada) y lo suma a la base."""
    def fit_predict(Xtr, ytr, Xte):
        base_tr, base_te = imdb_calibrated(Xtr, ytr, Xtr), imdb_calibrated(Xtr, ytr, Xte)
        pipe = Pipeline([("pre", make_pre(Xtr)), ("m", clone(estimator))])
        pipe.fit(Xtr, ytr - base_tr)
        return base_te + pipe.predict(Xte)
    return fit_predict


def _simple_pre(Xtr):
    genres = [c for c in Xtr.columns if c.startswith("genre_")]
    return ColumnTransformer([
        ("num", StandardScaler(), ["Year", "Runtime (mins)", "log_votes", "IMDb Rating"]),
        ("oh", OneHotEncoder(handle_unknown="ignore"), ["Title Type"]),
        ("gen", "passthrough", genres),
    ])


def _full_pre_factory(groups):
    return lambda Xtr: make_preprocessor(groups, "continuous")


def genre_shrinkage(Xtr, ytr, Xte, k=10.0):
    """Desvío medio por género con encogimiento hacia el desvío global (empirical-Bayes)."""
    base_tr, base_te = imdb_calibrated(Xtr, ytr, Xtr), imdb_calibrated(Xtr, ytr, Xte)
    dev = ytr - base_tr
    mu = dev.mean()
    genres = [c for c in Xtr.columns if c.startswith("genre_")]
    G = Xtr[genres].to_numpy(dtype=float)
    shrunk = np.array([mu + (dev[G[:, j] == 1].sum() - mu * (G[:, j] == 1).sum()) / ((G[:, j] == 1).sum() + k)
                       for j in range(len(genres))])
    Gt = Xte[genres].to_numpy(dtype=float)
    adj = np.where(Gt.sum(1) > 0, (Gt @ (shrunk - mu)) / np.maximum(Gt.sum(1), 1), 0.0)
    return base_te + mu + adj


def build_candidates(groups):
    full = _full_pre_factory(groups)
    cands = {
        "Media de tu nota": mean_model,
        "IMDb tal cual": imdb_raw,
        "IMDb calibrada (BASE)": imdb_calibrated,
        "Géneros con encogimiento": genre_shrinkage,
        "Ridge simple (géneros, año, duración, votos)": _deviation_model(_simple_pre, Ridge(alpha=30)),
        "Ridge con todas las variables": _deviation_model(full, Ridge(alpha=30)),
        "RandomForest (todas)": _deviation_model(full, RandomForestRegressor(200, min_samples_leaf=3, random_state=ROBUST_SEED, n_jobs=-1)),
        "GradientBoosting (todas)": _deviation_model(full, GradientBoostingRegressor(n_estimators=80, max_depth=2, learning_rate=0.05, subsample=0.7, random_state=ROBUST_SEED)),
    }
    ens_a, ens_b = cands["Ridge simple (géneros, año, duración, votos)"], cands["RandomForest (todas)"]
    cands["Promedio Ridge + RandomForest"] = lambda a, b, c: (ens_a(a, b, c) + ens_b(a, b, c)) / 2
    return cands


# --------------------------------------------------------------------------- #
# Validación y métricas
# --------------------------------------------------------------------------- #
def oof_predictions(fn, X, y):
    """Predicción fuera de muestra de cada título, promediada sobre ROBUST_REPEATS repartos distintos."""
    preds = np.zeros((ROBUST_REPEATS, len(y)))
    for r in range(ROBUST_REPEATS):
        for tr, te in KFold(5, shuffle=True, random_state=ROBUST_SEED + r).split(X):
            preds[r, te] = fn(X.iloc[tr], y[tr], X.iloc[te])
    return preds


# --------------------------------------------------------------------------- #
# Reporte
# --------------------------------------------------------------------------- #
def robustness_report():
    rng = np.random.default_rng(ROBUST_SEED)
    X, y_s = build()
    X = X.reset_index(drop=True)
    y = y_s.to_numpy(dtype=float)
    like = (y >= LIKE_THRESHOLD).astype(int)
    groups = feature_groups(X)
    cands = build_candidates(groups)
    n = len(y)
    print(f"n = {n} títulos puntuados · {ROBUST_REPEATS} repeticiones de CV de 5 folds · {N_BOOT} remuestreos bootstrap\n")

    oof = {}
    for name, fn in cands.items():
        oof[name] = oof_predictions(fn, X, y).mean(axis=0)
        print(f"  listo: {name}")

    base_name = "IMDb calibrada (BASE)"
    rows, boots = [], {}
    for name, p in oof.items():
        m = score_predictions(p, y, like)
        row = {"modelo": name, **m}
        if name != base_name:
            d_mae, d_auc = paired_bootstrap(p, oof[base_name], y, like, rng)
            boots[name] = (d_mae, d_auc)
            lo, hi = ci95(d_mae)
            row.update({"ΔMAE vs BASE": d_mae.mean(), "IC95 ΔMAE": f"[{lo:+.3f}, {hi:+.3f}]",
                        "P(mejor que BASE)": (d_mae < 0).mean(),
                        "ΔAUC vs BASE": d_auc.mean(), "IC95 ΔAUC": f"[{ci95(d_auc)[0]:+.3f}, {ci95(d_auc)[1]:+.3f}]"})
        rows.append(row)
    table = pd.DataFrame(rows).set_index("modelo")
    print("\n=== COMPARACIÓN (menor MAE/RMSE y mayor Spearman/AUC es mejor) ===")
    print(table.round(3).to_string())
    table.round(4).to_csv(MODELING_DIR / "robustness_comparison.csv")

    # ---- Poder estadístico ----------------------------------------------------------
    best = min(boots, key=lambda k: boots[k][0].mean())
    se = boots[best][0].std()
    print(f"\n=== PODER ESTADÍSTICO ===\nMejor candidato por MAE: {best}")
    print(f"Error estándar de la diferencia de MAE contra la base: {se:.3f}")
    print(f"Mejora mínima detectable (80 % de poder, 95 % de confianza) ≈ {2.8 * se:.2f} puntos de MAE")

    # ---- Control de permutación -----------------------------------------------------
    print("\n=== CONTROL DE PERMUTACIÓN (Ridge simple) ===")
    fn = cands["Ridge simple (géneros, año, duración, votos)"]
    real = np.abs(oof_predictions(fn, X, y).mean(axis=0) - y).mean() - np.abs(oof[base_name] - y).mean()
    null = []
    for s in range(150):
        # Se mezclan las filas de X respecto de y (se rompe la relación de tus gustos con los
        # géneros, etc.) pero se conserva la nota de IMDb de cada título pegada a TU nota real.
        perm = rng.permutation(n)
        Xp = X.copy()
        keep = ["IMDb Rating"]
        Xp[[c for c in X.columns if c not in keep]] = X[[c for c in X.columns if c not in keep]].iloc[perm].to_numpy()
        pp = np.zeros(n)
        for tr, te in KFold(5, shuffle=True, random_state=s).split(Xp):
            pp[te] = fn(Xp.iloc[tr], y[tr], Xp.iloc[te])
        bp = np.zeros(n)
        for tr, te in KFold(5, shuffle=True, random_state=s).split(Xp):
            bp[te] = imdb_calibrated(Xp.iloc[tr], y[tr], Xp.iloc[te])
        null.append(np.abs(pp - y).mean() - np.abs(bp - y).mean())
    null = np.array(null)
    print(f"ΔMAE real (modelo - base): {real:+.3f}")
    print(f"ΔMAE con las otras variables mezcladas al azar: media {null.mean():+.3f}, "
          f"percentil 5 {np.percentile(null, 5):+.3f}")
    print(f"Proporción de mezclas que igualan o superan al modelo real: {(null <= real).mean():.2f}")

    robust_learning_curve(cands, X, y, rng)
    forest_plot(boots)


def robust_learning_curve(cands, X, y, rng):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = ["IMDb calibrada (BASE)", "Ridge simple (géneros, año, duración, votos)", "RandomForest (todas)"]
    sizes, reps, n_test = [30, 50, 70, 90, 100], 25, 25
    res = {nm: {s: [] for s in sizes} for nm in names}
    for r in range(reps):
        idx = rng.permutation(len(y))
        te, pool = idx[:n_test], idx[n_test:]
        for s in sizes:
            tr = pool[:s]
            for nm in names:
                p = cands[nm](X.iloc[tr], y[tr], X.iloc[te])
                res[nm][s].append(np.abs(p - y[te]).mean())
    print("\n=== CURVA DE APRENDIZAJE (MAE en 25 títulos reservados; 25 repeticiones) ===")
    print("   n  | " + " | ".join(f"{nm[:22]:>22}" for nm in names) + " | Ridge−BASE")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = {names[0]: "tab:gray", names[1]: "tab:blue", names[2]: "tab:red"}
    for nm in names:
        m = np.array([np.mean(res[nm][s]) for s in sizes])
        se = np.array([np.std(res[nm][s]) / np.sqrt(reps) for s in sizes])
        ax.plot(sizes, m, "o-", color=colors[nm], label=nm.split(" (")[0])
        ax.fill_between(sizes, m - se, m + se, color=colors[nm], alpha=.15)
    for s in sizes:
        row = [np.mean(res[nm][s]) for nm in names]
        print(f"  {s:3d} | " + " | ".join(f"{v:22.3f}" for v in row) + f" | {row[1] - row[0]:+.3f}")
    ax.set(xlabel="títulos usados para entrenar", ylabel="error medio (MAE) en títulos no vistos",
           title="¿Mejora el modelo frente a IMDb al sumar datos?")
    ax.legend(); fig.tight_layout()
    fig.savefig(MODELING_DIR / "learning_curve_robust.png", dpi=140)
    print(f"Gráfico: {MODELING_DIR / 'learning_curve_robust.png'}")


def forest_plot(boots):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(boots)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i, nm in enumerate(names):
        d = boots[nm][0]
        lo, hi = ci95(d)
        ax.plot([lo, hi], [i, i], color="tab:blue", lw=3)
        ax.plot(d.mean(), i, "o", color="white", mec="tab:blue", ms=7)
    ax.axvline(0, color="gray", ls="--")
    ax.set_yticks(range(len(names))); ax.set_yticklabels([n[:34] for n in names])
    ax.set(xlabel="diferencia de MAE contra IMDb calibrada (izquierda = mejor que IMDb)",
           title="Cada modelo contra la nota de IMDb (IC 95 %)")
    fig.tight_layout()
    fig.savefig(MODELING_DIR / "model_vs_imdb.png", dpi=140)
    print(f"Gráfico: {MODELING_DIR / 'model_vs_imdb.png'}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--robust", action="store_true", help="correr también la prueba de robustez (~80 s)")
    ap.add_argument("--only-robust", action="store_true", help="correr solo la prueba de robustez")
    args = ap.parse_args(argv)
    if not args.only_robust:
        compare_models()
        learning_curve_report()
        plot_history()
        review_insights()
    if args.robust or args.only_robust:
        robustness_report()


if __name__ == "__main__":
    main()
