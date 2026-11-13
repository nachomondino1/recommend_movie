"""
CRISP-DM · Preparación de datos, VERSIÓN 1 (nota personal). La versión 2 usa prepare_titles.py.

Del JSON crudo de TMDB de los títulos de tus exportaciones de IMDb (~288) a una tabla lista para el modelado.

  - Format data     : aplanar el JSON de TMDB a una fila por título (parse_detail) y a columnas "estilo IMDb"
                      para títulos que no vienen de una exportación de IMDb (imdb_like_fields)
  - Integrate data  : tmdb_table() deja una sola tabla (data/02_data_preparation/tmdb.csv) que features.py
                      cruza con tus notas; load_reviews() trae tus reseñas, si las hay

El JSON crudo se baja en 01_data_understanding/tmdb_data.py y no se toca.

    python 02_data_preparation/prepare_tmdb.py     # (re)arma data/02_data_preparation/tmdb.csv
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


from functools import lru_cache

import numpy as np
import pandas as pd

from config import REVIEWS_CSV, TMDB_CSV
from tmdb_data import collect_raw

TOP_CAST = 8


def load_reviews() -> pd.DataFrame:
    """data/01_data_understanding/imdb/reviews.csv (Const, Title, Liked, Disliked, Date) -- vacío si no existe."""
    if not REVIEWS_CSV.exists():
        return pd.DataFrame(columns=["Const", "Title", "Liked", "Disliked", "Date"])
    return pd.read_csv(REVIEWS_CSV)


# --------------------------------------------------------------------------- #
# Format data: JSON de TMDB -> fila tabular
# --------------------------------------------------------------------------- #
def _join(values, sep="|") -> str:
    return sep.join(str(v) for v in values if v)


def parse_detail(detail: dict) -> dict:
    """Aplana el JSON crudo de TMDB a las columnas de data/02_data_preparation/tmdb.csv."""
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
        "poster_path": detail.get("poster_path"),
        "providers_flatrate": _join(detail.get("providers_flatrate_ar") or []),
        "budget": detail.get("budget"),
        "revenue": detail.get("revenue"),
        "n_seasons": detail.get("number_of_seasons"),
        "n_episodes": detail.get("number_of_episodes"),
        "release_date": detail.get("release_date") or detail.get("first_air_date"),
    }


def imdb_like_fields(detail: dict, parsed: dict) -> dict:
    """Aplana un detalle de TMDB a las columnas 'estilo IMDb' (Title, Year, Genres...)
    para títulos que no vienen de una exportación real de IMDb: búsqueda por nombre
    (predict) o catálogo ampliado (build_model.py)."""
    date_ = detail.get("release_date") or detail.get("first_air_date") or ""
    year = int(date_[:4]) if date_[:4].isdigit() else np.nan
    return {
        "Title": detail.get("title") or detail.get("name"),
        "Title Type": "Movie" if detail.get("media_type") == "movie" else "TV Series",
        "Year": year,
        "IMDb Rating": np.nan,  # -> build()/_engineer() usa tmdb_vote_average como sustituto
        "Runtime (mins)": parsed.get("tmdb_runtime"),
        "Genres": (parsed.get("tmdb_genres") or "").replace("|", ", "),
        "Num Votes": detail.get("vote_count"),
    }


# --------------------------------------------------------------------------- #
# Armado de la tabla
# --------------------------------------------------------------------------- #
def build_tmdb_table(force: bool = False) -> pd.DataFrame:
    """Aplana el JSON crudo de cada título (bajándolo si falta) y escribe data/02_data_preparation/tmdb.csv."""
    rows = [parse_detail(raw) for raw in collect_raw(force=force)]
    missing = [r["imdb_id"] for r in rows if not r["tmdb_found"]]
    df = pd.DataFrame(rows)
    df.to_csv(TMDB_CSV, index=False)
    print(f"\nGuardado: {TMDB_CSV}  ({len(df)} filas)")
    print(f"Sin match en TMDB: {len(missing)}  {missing or ''}")
    for col in ("overview", "keywords", "cast_top", "director"):
        n = (df[col].fillna("").astype(str).str.len() > 0).sum()
        print(f"  cobertura {col:15s}: {n}/{len(df)}")
    return df


@lru_cache(maxsize=1)
def tmdb_table() -> pd.DataFrame:
    """data/02_data_preparation/tmdb.csv como DataFrame (lo arma build_tmdb_table() si falta)."""
    if not TMDB_CSV.exists():
        build_tmdb_table()
    return pd.read_csv(TMDB_CSV)


if __name__ == "__main__":
    build_tmdb_table()
