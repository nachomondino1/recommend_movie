"""
Predecir la nota para un título por nombre (no hace falta que esté en la watchlist).

    python -m src.predict "Perfect Days"
    make predict TITLE="Perfect Days"

Busca el título en TMDB, arma la fila de features y aplica los modelos guardados
en models/ (los entrena si faltan).
"""

import argparse
import json

import numpy as np
import pandas as pd

from src.config import MODELS
from src.data import TMDBClient, parse_detail
from src.features import build, build_row
from src.model import load_models


def _imdb_like_fields(detail: dict, parsed: dict) -> dict:
    date = detail.get("release_date") or detail.get("first_air_date") or ""
    year = int(date[:4]) if date[:4].isdigit() else np.nan
    return {
        "Title": detail.get("title") or detail.get("name"),
        "Title Type": "Movie" if detail.get("media_type") == "movie" else "TV Series",
        "Year": year,
        "IMDb Rating": np.nan,  # -> build usa tmdb_vote_average como sustituto
        "Runtime (mins)": parsed.get("tmdb_runtime"),
        "Genres": (parsed.get("tmdb_genres") or "").replace("|", ", "),
        "Num Votes": detail.get("vote_count"),
    }


def predict_title(name: str) -> dict:
    detail = TMDBClient().fetch_by_name(name)
    parsed = parse_detail(detail)
    record = {**_imdb_like_fields(detail, parsed), **parsed}

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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("title", help="nombre de la película o serie")
    r = predict_title(ap.parse_args().title)

    print(f"\n{r['title']} ({r['year']}) · {r['type']}")
    print(f"  nota TMDB (referencia) : {r['tmdb_rating']:.1f}")
    print(f"  nota que le pondrías   : {r['pred_rating']}")
    print(f"  P(le pongas >= 7)      : {r['p_like']:.0%}")
    verdict = ("probablemente te guste" if r["p_like"] >= 0.6
               else "puede que no te enganche" if r["p_like"] <= 0.4
               else "moneda al aire")
    print(f"  -> {verdict}  (error típico ±1.3; tomar como orientación)")


if __name__ == "__main__":
    main()
