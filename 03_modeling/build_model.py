"""
CRISP-DM · Modelado · 2/3 «Build model» (definir, entrenar y usar el modelo).

Un solo archivo con todo lo que construye y aplica el modelo (la validación y las bases viven en
test_design.py; la comparación de resultados en assess_model.py):

  1. Pipeline    : preprocesado + estimadores
       - Regresión : RandomForest sobre el DESVÍO vs IMDb  -> pred = IMDb + desvío
       - Binario   : GradientBoosting sobre  Your Rating >= 7
  2. Entrenar    : fit_and_save() / load_models()  (guardan en 03_modeling/models/, git-ignored)
  3. Puntuar     : score_watchlist(), score_watched(), score_catalog() (TMDB discover)
  4. Predecir    : predict_title("Perfect Days")  (cualquier título por nombre)

    python 03_modeling/build_model.py                 # entrena y puntúa la watchlist y lo ya visto
    python 03_modeling/build_model.py catalog         # descubre y puntúa títulos fuera de tu watchlist
    python 03_modeling/build_model.py predict "X"     # nota predicha para un título por nombre

Detalle de decisiones y resultados: 03_modeling/modeling.md.
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import argparse
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder

from config import (CATALOG_CSV, CATALOG_SCORED_CSV, EXCLUDED_CSV, METRICS_CSV, MODELS, RATINGS_CSV,
                    SCORED_CSV, WATCHED_SCORED_CSV, WATCHLIST_CSV)
from features import build, build_row, build_rows, feature_groups
from test_design import LIKE_THRESHOLD, classification_cv, like_labels, regression_cv
from prepare_tmdb import imdb_like_fields, load_reviews, parse_detail, tmdb_table
from tmdb_data import TMDBClient


# --------------------------------------------------------------------------- #
# 1. Pipeline
# (OverviewEmbedder tiene que vivir en un módulo importable por nombre para que joblib la pueda
# deserializar; por eso el bloque final de este archivo se importa a sí mismo antes de correr.)
# --------------------------------------------------------------------------- #
class OverviewEmbedder(BaseEstimator, TransformerMixin):
    """TF-IDF de la sinopsis + TruncatedSVD, con n_components adaptativo.

    Con pocos títulos el vocabulario puede ser menor que n_components y el SVD
    falla; acá se recorta a lo disponible.
    """

    def __init__(self, n_components: int = 25, min_df: int = 3):
        self.n_components = n_components
        self.min_df = min_df

    @staticmethod
    def _flat(X):
        return np.asarray(X).ravel()

    def fit(self, X, y=None):
        self.tfidf_ = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                      min_df=self.min_df, max_features=800)
        Z = self.tfidf_.fit_transform(self._flat(X))
        k = max(2, min(self.n_components, Z.shape[1] - 1))
        self.svd_ = TruncatedSVD(n_components=k, random_state=42)
        self.svd_.fit(Z)
        return self

    def transform(self, X):
        return self.svd_.transform(self.tfidf_.transform(self._flat(X)))


def make_preprocessor(groups: dict, target_type: str) -> ColumnTransformer:
    # CV sembrado: sin esto, TargetEncoder (sklearn >=1.9) mezcla los folds sin
    # semilla y las predicciones cambian entre corridas.
    te_cv = KFold(n_splits=5, shuffle=True, random_state=42)
    return ColumnTransformer([
        ("num", StandardScaler(), groups["numeric"]),
        ("oh", OneHotEncoder(handle_unknown="ignore"), groups["onehot"]),
        ("dir", TargetEncoder(target_type=target_type, cv=te_cv), groups["target_enc"]),
        ("ovw", OverviewEmbedder(n_components=25, min_df=3), groups["overview"]),
        ("kw", CountVectorizer(min_df=4, binary=True), groups["keywords"]),
        ("gen", "passthrough", groups["genre"]),
    ])


def build_regressor(groups: dict) -> Pipeline:
    """OJO: el target es el DESVÍO (Your Rating - IMDb). Reconstruir con
    pred_nota = IMDb Rating + pipe.predict(X)."""
    return Pipeline([("pre", make_preprocessor(groups, "continuous")),
                     ("m", RandomForestRegressor(n_estimators=400, random_state=42))])


def build_classifier(groups: dict) -> Pipeline:
    return Pipeline([("pre", make_preprocessor(groups, "binary")),
                     ("m", GradientBoostingClassifier(random_state=42))])


REG_PATH = MODELS / "regressor.joblib"


CLF_PATH = MODELS / "classifier.joblib"

# --------------------------------------------------------------------------- #
# 2. Entrenar y guardar / cargar
# --------------------------------------------------------------------------- #
def fit_and_save() -> None:
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = like_labels(y)

    reg, clf = build_regressor(groups), build_classifier(groups)

    cv_mae = mean_absolute_error(y, imdb + cross_val_predict(reg, X, resid, cv=regression_cv()))
    cv_auc = roc_auc_score(like, cross_val_predict(clf, X, like, method="predict_proba",
                                                   cv=classification_cv())[:, 1])

    reg.fit(X, resid)
    clf.fit(X, like)
    joblib.dump(reg, REG_PATH)
    joblib.dump(clf, CLF_PATH)

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_train": int(len(X)),
        "ratings_csv_mtime": RATINGS_CSV.stat().st_mtime,
        "like_threshold": LIKE_THRESHOLD,
        "cv_mae_rating": round(float(cv_mae), 3),
        "cv_roc_auc_like": round(float(cv_auc), 3),
        "feature_columns": list(X.columns),
    }
    (MODELS / "meta.json").write_text(json.dumps(meta, indent=2))
    _append_history(meta)
    print(f"Modelos guardados en {MODELS}/  "
          f"(n={meta['n_train']}, CV MAE={meta['cv_mae_rating']}, CV AUC={meta['cv_roc_auc_like']})")


def _append_history(meta: dict) -> None:
    """Registra la trayectoria real de scores: una fila por tamaño de dataset."""
    row = {"date": meta["trained_at"][:10], "n_train": meta["n_train"],
           "cv_mae_rating": meta["cv_mae_rating"], "cv_roc_auc_like": meta["cv_roc_auc_like"]}
    hist = pd.read_csv(METRICS_CSV) if METRICS_CSV.exists() else pd.DataFrame()
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    hist = hist.drop_duplicates("n_train", keep="last").sort_values("n_train")
    hist.to_csv(METRICS_CSV, index=False)


# --------------------------------------------------------------------------- #
# Scoring de la watchlist
# --------------------------------------------------------------------------- #


def load_models():
    """Carga los modelos guardados; entrena si faltan, si ratings.csv es más nuevo o si no se pueden leer."""
    if not REG_PATH.exists() or not CLF_PATH.exists():
        print(">> No hay modelo guardado; entreno.")
        fit_and_save()
    elif RATINGS_CSV.stat().st_mtime > REG_PATH.stat().st_mtime:
        print("!! ratings.csv es más nuevo que el modelo guardado; re-entreno.")
        fit_and_save()
    try:
        return joblib.load(REG_PATH), joblib.load(CLF_PATH)
    except Exception as exc:   # p. ej. modelo guardado con una estructura de módulos anterior
        print(f"!! No pude leer el modelo guardado ({exc.__class__.__name__}); re-entreno.")
        fit_and_save()
        return joblib.load(REG_PATH), joblib.load(CLF_PATH)


# --------------------------------------------------------------------------- #
# 3. Puntuar: watchlist, ya visto y catálogo ampliado
# --------------------------------------------------------------------------- #
def score_watchlist() -> pd.DataFrame:
    reg, clf = load_models()
    X_tr, _ = build()

    wl = pd.read_csv(WATCHLIST_CSV)
    rated = set(pd.read_csv(RATINGS_CSV)["Const"].dropna())
    excluded = set(pd.read_csv(EXCLUDED_CSV)["Const"].dropna()) if EXCLUDED_CSV.exists() else set()
    n_drop_rated = int(wl["Const"].isin(rated).sum())
    n_drop_excluded = int(wl["Const"].isin(excluded).sum())
    keep = ~wl["Const"].isin(rated | excluded)   # sacar los ya puntuados y los "no me interesa"
    wl = wl[keep].reset_index(drop=True)

    X_wl, _ = build(WATCHLIST_CSV)
    X_wl = X_wl[keep.to_numpy()].reset_index(drop=True).reindex(columns=X_tr.columns, fill_value=0)

    wl["pred_rating"] = (X_wl["IMDb Rating"].to_numpy() + reg.predict(X_wl)).clip(1, 10)
    wl["p_like"] = clf.predict_proba(X_wl)[:, 1]
    wl["Directors"] = wl["Directors"].fillna("")
    wl = wl.merge(tmdb_table()[["imdb_id", "poster_path", "tmdb_runtime", "n_seasons",
                                "n_episodes", "providers_flatrate", "overview"]],
                  left_on="Const", right_on="imdb_id", how="left")
    reviews = load_reviews()[["Const", "Liked", "Disliked", "Date"]].rename(
        columns={"Liked": "my_liked", "Disliked": "my_disliked", "Date": "review_date"})
    wl = wl.merge(reviews, on="Const", how="left")
    if n_drop_rated:
        print(f"({n_drop_rated} títulos de la watchlist ya estaban puntuados; se omiten)")
    if n_drop_excluded:
        print(f"({n_drop_excluded} títulos marcados 'no me interesa'; se omiten)")

    cols = ["Const", "Title", "Year", "Title Type", "IMDb Rating", "Directors", "Genres", "URL",
            "Num Votes", "poster_path", "tmdb_runtime", "n_seasons", "n_episodes",
            "providers_flatrate", "overview", "my_liked", "my_disliked", "review_date",
            "pred_rating", "p_like"]
    out = (wl[cols].sort_values("pred_rating", ascending=False)
           .round({"pred_rating": 1, "p_like": 2}).reset_index(drop=True))
    out.to_csv(SCORED_CSV, index=False)
    print(f"\nGuardado: {SCORED_CSV}  ({len(out)} títulos)")
    print("\nTOP 10:")
    print(out.head(10).to_string())
    return out


# --------------------------------------------------------------------------- #
# Títulos ya vistos (todo ratings.csv), con tu reseña si la escribiste -- acá
# no hay nada que predecir, pred_rating/p_like son tu nota real, no una
# predicción.
# --------------------------------------------------------------------------- #
WATCHED_COLS = ["Const", "Title", "Year", "Title Type", "IMDb Rating", "Directors", "Genres",
                "URL", "Num Votes", "poster_path", "tmdb_runtime", "n_seasons", "n_episodes",
                "providers_flatrate", "overview", "my_liked", "my_disliked", "review_date",
                "pred_rating", "p_like"]


def score_watched() -> pd.DataFrame:
    ratings = pd.read_csv(RATINGS_CSV)
    ratings["Directors"] = ratings["Directors"].fillna("")
    reviews = load_reviews()[["Const", "Liked", "Disliked", "Date"]].rename(
        columns={"Liked": "my_liked", "Disliked": "my_disliked", "Date": "review_date"})
    df = ratings.merge(reviews, on="Const", how="left")
    df = df.merge(tmdb_table()[["imdb_id", "poster_path", "tmdb_runtime", "n_seasons",
                                "n_episodes", "providers_flatrate", "overview"]],
                  left_on="Const", right_on="imdb_id", how="left")
    df["pred_rating"] = df["Your Rating"].astype(float)
    df["p_like"] = (df["Your Rating"] >= LIKE_THRESHOLD).astype(float)

    out = df[WATCHED_COLS].sort_values("pred_rating", ascending=False).reset_index(drop=True)
    out.to_csv(WATCHED_SCORED_CSV, index=False)
    print(f"Guardado: {WATCHED_SCORED_CSV}  ({len(out)} títulos vistos)")
    return out

# --------------------------------------------------------------------------- #
# Catálogo ampliado, fuera de tu watchlist (descubre lo popular/trending en TMDB vía /discover y lo
# puntúa con los modelos ya entrenados, sin reentrenar)
# --------------------------------------------------------------------------- #
N_MOVIES = 100


N_TV = 50


MIN_VOTES = 100


def _known_ids() -> set[str]:
    """Const (imdb_id) que no deben duplicarse en el catálogo: ya puntuados, ya en
    la watchlist real, o marcados 'no me interesa'."""
    ids = (set(pd.read_csv(RATINGS_CSV)["Const"].dropna())
           | set(pd.read_csv(WATCHLIST_CSV)["Const"].dropna()))
    if EXCLUDED_CSV.exists():
        ids |= set(pd.read_csv(EXCLUDED_CSV)["Const"].dropna())
    return ids


def discover_catalog() -> pd.DataFrame:
    """Descubre títulos populares en TMDB (fuera de ratings/watchlist/excluded) y
    guarda sus columnas aplanadas (IMDb-like + TMDB) en CATALOG_CSV."""
    client = TMDBClient()
    candidates = client.discover("movie", N_MOVIES, MIN_VOTES) + client.discover("tv", N_TV, MIN_VOTES)
    known = _known_ids()
    print(f"Candidatos del catálogo (TMDB discover): {len(candidates)}")

    rows, seen = [], set()
    for i, c in enumerate(candidates, 1):
        detail = client.fetch_by_tmdb_id(c["media_type"], c["id"])
        parsed = parse_detail(detail)
        imdb_id = parsed.get("imdb_id")
        if parsed["tmdb_found"] and imdb_id and imdb_id not in known and imdb_id not in seen:
            seen.add(imdb_id)
            rows.append({**imdb_like_fields(detail, parsed), **parsed})
        if i % 25 == 0 or i == len(candidates):
            print(f"  {i}/{len(candidates)}")

    df = pd.DataFrame(rows)
    df.to_csv(CATALOG_CSV, index=False)
    print(f"\nGuardado: {CATALOG_CSV}  ({len(df)} títulos fuera de tu watchlist)")
    return df


def score_catalog() -> pd.DataFrame:
    """Puntúa el catálogo con los modelos ya entrenados (no reentrena) y guarda
    CATALOG_SCORED_CSV con las mismas columnas que watchlist_scored.csv."""
    cat = discover_catalog()
    if cat.empty:
        out = cat.reindex(columns=["Const", "Title", "Year", "Title Type", "IMDb Rating",
                                   "Directors", "Genres", "URL", "Num Votes", "poster_path",
                                   "tmdb_runtime", "n_seasons", "n_episodes", "providers_flatrate",
                                   "overview", "my_liked", "my_disliked", "review_date",
                                   "pred_rating", "p_like"])
        out.to_csv(CATALOG_SCORED_CSV, index=False)
        return out

    meta = json.loads((MODELS / "meta.json").read_text()) if (MODELS / "meta.json").exists() else {}
    X = build_rows(cat.to_dict("records"))
    if meta.get("feature_columns"):
        X = X.reindex(columns=meta["feature_columns"], fill_value=0)

    reg, clf = load_models()
    cat["pred_rating"] = (X["IMDb Rating"].to_numpy() + reg.predict(X)).clip(1, 10)
    cat["p_like"] = clf.predict_proba(X)[:, 1]
    cat["IMDb Rating"] = cat["IMDb Rating"].fillna(cat["tmdb_vote_average"])
    cat["Directors"] = cat["director"].fillna("").str.replace("|", ", ", regex=False)
    cat["URL"] = "https://www.imdb.com/title/" + cat["imdb_id"]
    cat["Const"] = cat["imdb_id"]

    reviews = load_reviews()[["Const", "Liked", "Disliked", "Date"]].rename(
        columns={"Liked": "my_liked", "Disliked": "my_disliked", "Date": "review_date"})
    cat = cat.merge(reviews, on="Const", how="left")

    cols = ["Const", "Title", "Year", "Title Type", "IMDb Rating", "Directors", "Genres", "URL",
            "Num Votes", "poster_path", "tmdb_runtime", "n_seasons", "n_episodes",
            "providers_flatrate", "overview", "my_liked", "my_disliked", "review_date",
            "pred_rating", "p_like"]
    out = (cat[cols].sort_values("pred_rating", ascending=False)
           .round({"pred_rating": 1, "p_like": 2}).reset_index(drop=True))
    out.to_csv(CATALOG_SCORED_CSV, index=False)
    print(f"Guardado: {CATALOG_SCORED_CSV}  ({len(out)} títulos)")
    print("\nTOP 10 del catálogo:")
    print(out.head(10).to_string())
    return out

# --------------------------------------------------------------------------- #
# 4. Predecir un título por nombre (no hace falta que esté en la watchlist)
# --------------------------------------------------------------------------- #
def predict_title(name: str) -> dict:
    detail = TMDBClient().fetch_by_name(name)
    parsed = parse_detail(detail)
    record = {**imdb_like_fields(detail, parsed), **parsed}

    X = build_row(record)
    meta = json.loads((MODELS / "meta.json").read_text()) if (MODELS / "meta.json").exists() else {}
    cols = meta.get("feature_columns") or build()[0].columns
    X = X.reindex(columns=cols, fill_value=0)

    reg, clf = load_models()
    pred_rating = float(np.clip(X["IMDb Rating"].iloc[0] + reg.predict(X)[0], 1, 10))
    p_like = float(clf.predict_proba(X)[0, 1])
    return {
        "title": record["Title"],
        "year": None if pd.isna(record["Year"]) else int(record["Year"]),
        "type": record["Title Type"],
        "tmdb_rating": detail.get("vote_average"),
        "pred_rating": round(pred_rating, 1),
        "p_like": round(p_like, 2),
    }


# --------------------------------------------------------------------------- #
# Línea de comandos
# --------------------------------------------------------------------------- #
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", default="train", choices=["train", "catalog", "predict"])
    ap.add_argument("title", nargs="?", help="nombre de la película o serie (solo para 'predict')")
    args = ap.parse_args(argv)
    if args.cmd == "train":
        fit_and_save()
        score_watchlist()
        score_watched()
    elif args.cmd == "catalog":
        score_catalog()
    else:
        if not args.title:
            ap.error("predict necesita el nombre del título")
        r = predict_title(args.title)
        print(f"\n{r['title']} ({r['year']}) · {r['type']}")
        print(f"  nota TMDB (referencia) : {r['tmdb_rating']:.1f}")
        print(f"  nota que le pondrías   : {r['pred_rating']}")
        print(f"  P(le pongas >= 7)      : {r['p_like']:.0%}")
        verdict = ("probablemente te guste" if r["p_like"] >= 0.6
                   else "puede que no te enganche" if r["p_like"] <= 0.4 else "moneda al aire")
        print(f"  -> {verdict}  (error típico ±1.3; tomar como orientación)")


if __name__ == "__main__":
    import build_model   # se importa a sí mismo: así las clases del pipeline quedan en "build_model" y no en "__main__"
    build_model.main()
