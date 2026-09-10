"""
CRISP-DM: Data Preparation (parte 2) - matriz de features.

Combina metadatos de IMDb (nota IMDb, duración, año, votos, géneros, tipo y
derivadas) con contenido de TMDB (sinopsis, keywords, director, idioma, métricas).

Devuelve X con columnas "crudas": el texto queda como string y las categóricas
como string; la vectorización pesada (TF-IDF, SVD, target encoding) se hace
dentro del pipeline de sklearn para que respete la validación cruzada.

    from src.features import build, feature_groups
"""

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RATINGS_CSV, WATCHLIST_CSV
from src.data import tmdb_table

TOP_LANGS = 4

NUMERIC = [
    "IMDb Rating", "Runtime (mins)", "Year", "log_votes",
    "n_genres", "years_since_release", "is_franchise", "runtime_missing",
    "tmdb_vote_average", "log_tmdb_votes", "tmdb_popularity",
    "log_budget", "n_seasons", "n_episodes",
]
ONEHOT = ["Title Type", "lang_grouped", "media_type"]
TARGET_ENC = ["director"]
TEXT_OVERVIEW = "overview"
TEXT_KEYWORDS = "keywords_txt"


def _franchise_flag(titles: pd.Series) -> pd.Series:
    pat = r"\b(?:\d+|II|III|IV|V|VI|VII|VIII|IX|X|part|chapter|vol|volume)\b"
    return titles.str.contains(pat, case=False, regex=True).fillna(False).astype(int)


def build(csv: Path = RATINGS_CSV) -> tuple[pd.DataFrame, pd.Series | None]:
    """(X, y). y es None si el CSV no trae 'Your Rating' (p. ej. la watchlist)."""
    df = pd.read_csv(csv).merge(tmdb_table(), left_on="Const", right_on="imdb_id", how="left")

    # --- numéricas IMDb ---
    df["IMDb Rating"] = (df["IMDb Rating"].fillna(df["tmdb_vote_average"])
                         .fillna(df["IMDb Rating"].median()))
    df["log_votes"] = np.log10(df["Num Votes"].fillna(0).clip(lower=1))
    df["runtime_missing"] = df["Runtime (mins)"].isna().astype(int)
    df["Runtime (mins)"] = df["Runtime (mins)"].fillna(df["Runtime (mins)"].median())
    df["n_genres"] = df["Genres"].fillna("").str.split(", ").str.len()
    rated_year = pd.to_datetime(df.get("Date Rated"), errors="coerce").dt.year
    df["years_since_release"] = (rated_year - df["Year"]).clip(lower=0)
    df["is_franchise"] = _franchise_flag(df["Title"])

    # --- numéricas TMDB ---
    df["log_tmdb_votes"] = np.log10(df["tmdb_vote_count"].fillna(0).clip(lower=1))
    df["log_budget"] = np.log10(df["budget"].fillna(0).clip(lower=1))
    for col in ("tmdb_vote_average", "tmdb_popularity", "n_seasons", "n_episodes"):
        df[col] = df[col].fillna(0)

    # --- categóricas ---
    df["media_type"] = df["media_type"].fillna("movie")
    df["director"] = df["director"].fillna("Unknown")
    top = df["original_language"].value_counts().head(TOP_LANGS).index
    df["lang_grouped"] = (df["original_language"].where(df["original_language"].isin(top), "other")
                          .fillna("other"))

    # --- texto ---
    df["overview"] = df["overview"].fillna("")
    df["keywords_txt"] = df["keywords"].fillna("").str.replace("|", " ", regex=False)

    # --- géneros multi-hot (de IMDb) ---
    genres = df["Genres"].str.get_dummies(sep=", ")
    genres.columns = [f"genre_{c}" for c in genres.columns]

    X = pd.concat([df[NUMERIC + ONEHOT + TARGET_ENC + [TEXT_OVERVIEW, TEXT_KEYWORDS]], genres],
                  axis=1)
    X[NUMERIC] = X[NUMERIC].apply(lambda c: c.fillna(c.median())).fillna(0)

    y = df["Your Rating"] if "Your Rating" in df and df["Your Rating"].notna().any() else None
    return X, y


def feature_groups(X: pd.DataFrame) -> dict:
    return {
        "numeric": NUMERIC,
        "onehot": ONEHOT,
        "target_enc": TARGET_ENC,
        "overview": TEXT_OVERVIEW,
        "keywords": TEXT_KEYWORDS,
        "genre": [c for c in X.columns if c.startswith("genre_")],
    }


if __name__ == "__main__":
    X, y = build()
    print(f"X entrenamiento: {X.shape}  |  y: {None if y is None else y.shape}")
    Xw, _ = build(WATCHLIST_CSV)
    print(f"X watchlist:     {Xw.shape}")
