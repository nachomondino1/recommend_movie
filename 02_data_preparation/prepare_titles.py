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
    return out


if __name__ == "__main__":
    t = build()
    t.to_csv(OUT, index=False)
    print(f"Guardado: {OUT}  ({len(t)} títulos, {t.shape[1]} columnas)")
    print(f"  películas {int((t.is_tv == 0).sum())} · series {int(t.is_tv.sum())}")
    print(f"  géneros como variable: {sum(c.startswith('g_') for c in t.columns)} · plataformas: {sum(c.startswith('p_') for c in t.columns)}")
