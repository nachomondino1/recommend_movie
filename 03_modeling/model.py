"""
CRISP-DM: Modelado (+ scoring).

Pipeline final (ver 03_modeling/modeling.md):
    - Regresión : RandomForest sobre el DESVÍO vs IMDb  -> pred = IMDb + desvío
    - Binario   : GradientBoosting sobre  Your Rating >= 7

    python 03_modeling/model.py   # entrena, guarda en models/ y puntúa la watchlist y lo ya visto
                                  # (los diagnósticos están en 04_evaluation/evaluate.py)
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import json
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict

from config import (EXCLUDED_CSV, METRICS_CSV, MODELS, RATINGS_CSV, SCORED_CSV,
                    WATCHED_SCORED_CSV, WATCHLIST_CSV)
from features import build, feature_groups
from pipeline import (LIKE_THRESHOLD, OverviewEmbedder, build_classifier,  # noqa: F401
                      build_regressor)
from tmdb_data import load_reviews, tmdb_table

REG_PATH = MODELS / "regressor.joblib"
CLF_PATH = MODELS / "classifier.joblib"


# --------------------------------------------------------------------------- #
# Entrenar y guardar / cargar
# --------------------------------------------------------------------------- #
def fit_and_save() -> None:
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = (y >= LIKE_THRESHOLD).astype(int)

    reg, clf = build_regressor(groups), build_classifier(groups)

    cv_mae = mean_absolute_error(
        y, imdb + cross_val_predict(reg, X, resid, cv=KFold(5, shuffle=True, random_state=42)))
    cv_auc = roc_auc_score(
        like, cross_val_predict(clf, X, like, method="predict_proba",
                                cv=StratifiedKFold(5, shuffle=True, random_state=42))[:, 1])

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


def load_models():
    if not REG_PATH.exists() or not CLF_PATH.exists():
        print(">> No hay modelo guardado; entreno.")
        fit_and_save()
    elif RATINGS_CSV.stat().st_mtime > REG_PATH.stat().st_mtime:
        print("!! ratings.csv es más nuevo que el modelo guardado; re-entreno.")
        fit_and_save()
    return joblib.load(REG_PATH), joblib.load(CLF_PATH)


# --------------------------------------------------------------------------- #
# Scoring de la watchlist
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


if __name__ == "__main__":
    fit_and_save()
    score_watchlist()
    score_watched()
