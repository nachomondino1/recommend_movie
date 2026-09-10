"""
Fase Data Preparation - enriquecimiento con TMDB.

1. Junta todos los ids de IMDb de ratings.csv + watchlist.csv
2. Descarga (con caché) el detalle de TMDB de cada uno
3. Aplana los campos útiles a data/processed/tmdb.csv

Uso:
    ./venv/bin/python data_preparation/enrich_tmdb.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import PROCESSED, RATINGS_CSV, WATCHLIST_CSV
from data_preparation.tmdb_client import TMDBClient

TOP_CAST = 8


def all_imdb_ids() -> list[str]:
    ids = set()
    for csv in (RATINGS_CSV, WATCHLIST_CSV):
        ids.update(pd.read_csv(csv)["Const"].dropna())
    return sorted(ids)


def _join(values, sep="|") -> str:
    return sep.join(str(v) for v in values if v)


def parse(detail: dict) -> dict:
    if not detail.get("tmdb_found"):
        return {"imdb_id": detail.get("imdb_id"), "tmdb_found": False}

    mt = detail.get("media_type")
    credits = detail.get("credits", {})
    cast = [c["name"] for c in credits.get("cast", [])[:TOP_CAST]]

    if mt == "movie":
        directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
        runtime = detail.get("runtime")
    else:
        directors = [p["name"] for p in detail.get("created_by", [])]
        ert = detail.get("episode_run_time") or []
        runtime = ert[0] if ert else None

    kw = detail.get("keywords", {})
    keywords = [k["name"] for k in (kw.get("keywords") or kw.get("results") or [])]

    return {
        "imdb_id": detail["imdb_id"],
        "tmdb_found": True,
        "media_type": mt,
        "tmdb_title": detail.get("title") or detail.get("name"),
        "overview": detail.get("overview") or "",
        "tmdb_genres": _join(g["name"] for g in detail.get("genres", [])),
        "keywords": _join(keywords),
        "cast_top": _join(cast),
        "director": _join(directors),
        "tmdb_runtime": runtime,
        "original_language": detail.get("original_language"),
        "countries": _join(c["iso_3166_1"] for c in detail.get("production_countries", [])),
        "tmdb_vote_average": detail.get("vote_average"),
        "tmdb_vote_count": detail.get("vote_count"),
        "tmdb_popularity": detail.get("popularity"),
        "budget": detail.get("budget"),
        "revenue": detail.get("revenue"),
        "n_seasons": detail.get("number_of_seasons"),
        "n_episodes": detail.get("number_of_episodes"),
        "release_date": detail.get("release_date") or detail.get("first_air_date"),
    }


def main() -> None:
    ids = all_imdb_ids()
    client = TMDBClient()
    print(f"Títulos únicos a resolver: {len(ids)}")

    rows, missing = [], []
    for i, imdb_id in enumerate(ids, 1):
        detail = client.fetch(imdb_id)
        row = parse(detail)
        rows.append(row)
        if not row["tmdb_found"]:
            missing.append(imdb_id)
        if i % 25 == 0 or i == len(ids):
            print(f"  {i}/{len(ids)}")

    df = pd.DataFrame(rows)
    out = PROCESSED / "tmdb.csv"
    df.to_csv(out, index=False)
    print(f"\nGuardado: {out}  ({len(df)} filas)")
    print(f"Sin match en TMDB: {len(missing)}  {missing if missing else ''}")
    print("\nCobertura de campos clave:")
    for col in ("overview", "keywords", "cast_top", "director"):
        non_empty = (df[col].fillna("").astype(str).str.len() > 0).sum()
        print(f"  {col:16s}: {non_empty}/{len(df)}")


if __name__ == "__main__":
    main()
