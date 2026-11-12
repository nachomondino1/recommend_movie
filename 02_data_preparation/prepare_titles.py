"""
CRISP-DM · Preparación de datos (versión "qué hace que una película tenga buena nota").

Arma una fila por título a partir del JSON crudo de TMDB del catálogo (no usa tus notas de IMDb) con la variable
respuesta (la nota pública de TMDB) y las variables que podrían explicarla:

  - Format / Clean : un solo vocabulario de géneros (los de series se llevan al de películas), duplicados fuera
  - Construct      : indicadores 0/1 por género y por plataforma, cantidad de títulos del director, largo de la sinopsis
  - Select         : popularidad y cantidad de votos van en un grupo aparte ("circulares"): dependen de la nota,
                     no la explican, así que el análisis principal las deja afuera

    python 02_data_preparation/prepare_titles.py     # escribe data/02_data_preparation/titles_features.csv
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import json

import numpy as np
import pandas as pd

from config import PREP_DIR

RAW = Path(__file__).resolve().parents[1] / "data" / "01_data_understanding" / "tmdb" / "tmdb_titles.jsonl"
CREDITS = RAW.with_name("credits.jsonl")      # lo baja 01_data_understanding/collect_initial_data/tmdb/fetch_credits.py
TOP_N = 5                                    # cuántos del reparto cuentan como "elenco principal"
STAR_POPULARITY = 15                         # un actor con más popularidad que esto en TMDB se cuenta como "conocido"
OUT = PREP_DIR / "titles_features.csv"
MIN_GENRE_N = 100       # un género entra como variable si tiene al menos tantos títulos
N_PROVIDERS = 12        # plataformas más frecuentes que entran como variable

# Géneros de series de TMDB -> vocabulario de películas ([] = se descarta)
GENRE_MAP = {
    "Sci-Fi & Fantasy": ["Ciencia ficción", "Fantasía"], "Action & Adventure": ["Acción", "Aventura"],
    "War & Politics": ["Bélica"], "Kids": ["Familia"], "Película de TV": [], "Soap": [], "Talk": [], "News": [],
}


def load_raw() -> pd.DataFrame:
    df = pd.DataFrame(json.loads(line) for line in RAW.open())
    return df.drop_duplicates(["media_type", "tmdb_id"]).reset_index(drop=True)


def build() -> pd.DataFrame:
    df = load_raw()
    genres = df["genres"].map(lambda gs: sorted({m for g in gs for m in GENRE_MAP.get(g, [g])}))
    out = pd.DataFrame({
        "tmdb_id": df["tmdb_id"], "media_type": df["media_type"], "title": df["title"], "year_raw": df["year"],
        # --- respuesta ---
        "rating": df["vote_average"],
        # --- circulares (no explican la nota: dependen de ella) ---
        "votes": df["vote_count"], "popularity": df["popularity"],
        # --- variables ---
        "is_tv": (df["media_type"] == "tv").astype(int),
        "year": df["year"].astype(float),
        "runtime": pd.to_numeric(df["runtime"], errors="coerce"),
        "seasons": pd.to_numeric(df["seasons"], errors="coerce").fillna(0),
        "n_genres": genres.map(len),
        "n_directors": df["directors"].map(len),
        "director": df["directors"].map(lambda d: d[0] if d else "(sin director)"),
        "n_providers": df["providers"].map(len),
        "overview_len": df["overview"].fillna("").str.len(),
        "overview": df["overview"].fillna(""),
    })
    out["runtime_missing"] = out["runtime"].isna().astype(int)
    out["has_director"] = (out["director"] != "(sin director)").astype(int)
    out["has_overview"] = (out["overview_len"] > 0).astype(int)
    out["director_n_titles"] = out["director"].map(out["director"].value_counts()).where(out["has_director"] == 1, 0)
    for g, n in genres.explode().value_counts().items():
        if n >= MIN_GENRE_N:
            out[f"g_{g}"] = genres.map(lambda gs, g=g: int(g in gs))
    top = df["providers"].explode().value_counts().head(N_PROVIDERS).index
    for p in top:
        out[f"p_{p}"] = df["providers"].map(lambda ps, p=p: int(p in ps))
    return add_credits(out)


def add_credits(out: pd.DataFrame) -> pd.DataFrame:
    """Suma variables de elenco y equipo si ya se bajaron los créditos (fetch_credits.py)."""
    if not CREDITS.exists():
        return out
    cr = pd.DataFrame(json.loads(line) for line in CREDITS.open())
    out = out.merge(cr, on=["media_type", "tmdb_id"], how="left")
    cast = out["cast"].map(lambda c: c if isinstance(c, list) else [])
    top = cast.map(lambda c: c[:TOP_N])
    # cuántos títulos tiene en el catálogo cada actor: una medida de trayectoria, sin mirar la nota
    freq = pd.Series([a["id"] for c in top for a in c]).value_counts()
    out["has_credits"] = cast.map(len).gt(0).astype(int)
    out["cast_ids"] = top.map(lambda c: "|".join(str(a["id"]) for a in c))
    out["cast_pop_mean"] = top.map(lambda c: np.mean([a["popularity"] or 0 for a in c]) if c else 0.0)
    out["cast_pop_max"] = top.map(lambda c: max([a["popularity"] or 0 for a in c], default=0.0))
    out["cast_n_stars"] = top.map(lambda c: sum((a["popularity"] or 0) >= STAR_POPULARITY for a in c))
    out["cast_titles_mean"] = top.map(lambda c: np.mean([freq.get(a["id"], 0) for a in c]) if c else 0.0)
    for col, name in [("writers", "writers_ids"), ("composers", "composers_ids"), ("cinematographers", "dop_ids")]:
        out[name] = out[col].map(lambda l: "|".join(str(x["id"]) for x in l[:3]) if isinstance(l, list) else "")
    return out.drop(columns=["cast", "writers", "composers", "cinematographers", "directors"], errors="ignore")


if __name__ == "__main__":
    t = build()
    t.to_csv(OUT, index=False)
    print(f"Guardado: {OUT}  ({len(t)} títulos, {t.shape[1]} columnas)")
    print(f"  películas {int((t.is_tv == 0).sum())} · series {int(t.is_tv.sum())}")
    print(f"  géneros como variable: {sum(c.startswith('g_') for c in t.columns)} · plataformas: {sum(c.startswith('p_') for c in t.columns)}")
