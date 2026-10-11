"""
CRISP-DM: curar la watchlist a mano -- marcar un título como visto o descartado.

    make watched TITLE="Perfect Days" RATING=8   # agrega a data/ratings.csv
    make skip TITLE="Some show"                  # agrega a data/excluded.csv

    python -m src.curate watched "Perfect Days" 8
    python -m src.curate skip "Some show"

No hace falta sacar el título de data/watchlist.csv en ningún caso: score_watchlist()
ya lo omite (por estar puntuado o por estar excluido). Después de usar cualquiera de
los dos, correr 'make update' para que el modelo y el dashboard reflejen el cambio.
"""

import argparse
from datetime import date

import numpy as np
import pandas as pd

from src.config import EXCLUDED_CSV, RATINGS_CSV, WATCHLIST_CSV
from src.data import TMDBClient, parse_detail

RATINGS_COLUMNS = [
    "Const", "Your Rating", "Date Rated", "Title", "Original Title", "URL",
    "Title Type", "IMDb Rating", "Runtime (mins)", "Year", "Genres",
    "Num Votes", "Release Date", "Directors",
]
EXCLUDED_COLUMNS = ["Const", "Title", "Date"]


def mark_watched(name: str, rating: int) -> dict:
    detail = TMDBClient().fetch_by_name(name)
    imdb_id = detail.get("imdb_id")
    if not imdb_id:
        raise SystemExit(f"TMDB no devolvió un imdb_id para {name!r}; no se puede registrar.")

    ratings = pd.read_csv(RATINGS_CSV)
    if imdb_id in set(ratings["Const"]):
        raise SystemExit(f"{name!r} ({imdb_id}) ya está en {RATINGS_CSV}.")

    parsed = parse_detail(detail)
    release = detail.get("release_date") or detail.get("first_air_date") or ""
    year = int(release[:4]) if release[:4].isdigit() else np.nan

    row = {
        "Const": imdb_id,
        "Your Rating": rating,
        "Date Rated": date.today().isoformat(),
        "Title": detail.get("title") or detail.get("name"),
        "Original Title": detail.get("original_title") or detail.get("original_name"),
        "URL": f"https://www.imdb.com/title/{imdb_id}",
        "Title Type": "Movie" if detail.get("media_type") == "movie" else "TV Series",
        "IMDb Rating": np.nan,  # -> build() usa tmdb_vote_average como sustituto
        "Runtime (mins)": parsed.get("tmdb_runtime"),
        "Year": year,
        "Genres": (parsed.get("tmdb_genres") or "").replace("|", ", "),
        "Num Votes": detail.get("vote_count"),
        "Release Date": release,
        "Directors": (parsed.get("director") or "").replace("|", ", "),
    }
    ratings = pd.concat([ratings, pd.DataFrame([row])[RATINGS_COLUMNS]], ignore_index=True)
    ratings.to_csv(RATINGS_CSV, index=False)
    print(f"Agregado a {RATINGS_CSV}: {row['Title']} ({year}) · tu nota: {rating}")
    print("Corré 'make update' para re-entrenar y actualizar el dashboard.")
    return row


def mark_skip(name: str) -> dict:
    wl = pd.read_csv(WATCHLIST_CSV)
    matches = wl[wl["Title"].str.contains(name, case=False, na=False, regex=False)]
    if matches.empty:
        raise SystemExit(f"No encontré {name!r} en {WATCHLIST_CSV}.")
    if len(matches) > 1:
        opts = "\n".join(f"  - {t} ({y})" for t, y in zip(matches["Title"], matches["Year"]))
        raise SystemExit(f"Varios títulos de la watchlist coinciden con {name!r}, sé más específico:\n{opts}")

    row = matches.iloc[0]
    excluded = pd.read_csv(EXCLUDED_CSV) if EXCLUDED_CSV.exists() else pd.DataFrame(columns=EXCLUDED_COLUMNS)
    if row["Const"] in set(excluded["Const"]):
        raise SystemExit(f"{row['Title']!r} ya estaba marcado como 'no me interesa'.")

    new_row = {"Const": row["Const"], "Title": row["Title"], "Date": date.today().isoformat()}
    excluded = pd.concat([excluded, pd.DataFrame([new_row])], ignore_index=True)
    excluded.to_csv(EXCLUDED_CSV, index=False)
    print(f"Marcado 'no me interesa': {row['Title']} ({row['Year']})")
    print("Corré 'make update' para que desaparezca del dashboard.")
    return new_row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_watched = sub.add_parser("watched", help="marcar como vista y puntuada")
    p_watched.add_argument("title")
    p_watched.add_argument("rating", type=int)

    p_skip = sub.add_parser("skip", help="excluir de la watchlist puntuada sin puntuarla")
    p_skip.add_argument("title")

    args = ap.parse_args()
    if args.cmd == "watched":
        if not 1 <= args.rating <= 10:
            ap.error("RATING debe estar entre 1 y 10")
        mark_watched(args.title, args.rating)
    else:
        mark_skip(args.title)


if __name__ == "__main__":
    main()
