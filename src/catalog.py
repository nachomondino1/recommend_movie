"""
CRISP-DM: Deployment - catálogo ampliado, fuera de la watchlist (Fase 6).

`score_watchlist()` sólo puntúa lo que el usuario ya puso en su watchlist de IMDb.
Este módulo amplía esa lista con lo más popular/trending en TMDB (vía /discover),
para que el dashboard también pueda recomendar títulos que el usuario nunca agregó.

    python -m src.catalog     # descubre y puntúa -> outputs/catalog_scored.csv
"""

import json

import pandas as pd

from src.config import (CATALOG_CSV, CATALOG_SCORED_CSV, EXCLUDED_CSV, MODELS,
                        RATINGS_CSV, WATCHLIST_CSV)
from src.data import TMDBClient, imdb_like_fields, load_reviews, parse_detail
from src.features import build_rows
from src.model import load_models

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


def build_catalog() -> pd.DataFrame:
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
    cat = build_catalog()
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


if __name__ == "__main__":
    score_catalog()
