"""
Fase Data Preparation - construcción de la matriz de features.

Combina:
    - Metadatos de IMDb (ratings.csv): nota IMDb, duración, año, votos, géneros,
      tipo, y derivadas (n_genres, is_franchise, years_since_release...).
    - Contenido de TMDB (processed/tmdb.csv): sinopsis, keywords, director,
      idioma original, media_type, métricas de TMDB.

Devuelve un DataFrame X con columnas "crudas" (texto como string, categóricas
como string). La vectorización pesada (TF-IDF, SVD, target encoding) se hace
dentro del pipeline de sklearn para que respete la validación cruzada.

Uso como módulo:
    from data_preparation.build_features import build, feature_groups
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import PROCESSED, RATINGS_CSV, WATCHLIST_CSV

TOP_LANGS = 4  # idiomas más frecuentes que quedan como categoría propia

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


def _load_merged(ratings_csv: Path) -> pd.DataFrame:
    imdb = pd.read_csv(ratings_csv)
    tmdb = pd.read_csv(PROCESSED / "tmdb.csv")
    return imdb.merge(tmdb, left_on="Const", right_on="imdb_id", how="left")


def build(ratings_csv: Path = RATINGS_CSV) -> tuple[pd.DataFrame, pd.Series | None]:
    df = _load_merged(ratings_csv).copy()

    # --- numéricas IMDb ---
    # IMDb Rating faltante (títulos sin estrenar en la watchlist): usar el voto
    # promedio de TMDB como sustituto, y si tampoco está, la mediana.
    df["IMDb Rating"] = df["IMDb Rating"].fillna(df["tmdb_vote_average"]).fillna(
        df["IMDb Rating"].median()
    )
    df["log_votes"] = np.log10(df["Num Votes"].fillna(0).clip(lower=1))
    df["runtime_missing"] = df["Runtime (mins)"].isna().astype(int)
    df["Runtime (mins)"] = df["Runtime (mins)"].fillna(df["Runtime (mins)"].median())
    df["n_genres"] = df["Genres"].fillna("").str.split(", ").str.len()
    # "años desde el estreno al puntuar": solo aplica a lo ya visto. En la
    # watchlist no hay Date Rated -> queda NaN y se imputa abajo.
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
    df["lang_grouped"] = df["original_language"].where(
        df["original_language"].isin(top), other="other"
    ).fillna("other")

    # --- texto ---
    df["overview"] = df["overview"].fillna("")
    df["keywords_txt"] = df["keywords"].fillna("").str.replace("|", " ", regex=False)

    # --- géneros multi-hot (de IMDb) ---
    genres = df["Genres"].str.get_dummies(sep=", ")
    genres.columns = [f"genre_{c}" for c in genres.columns]

    cols = NUMERIC + ONEHOT + TARGET_ENC + [TEXT_OVERVIEW, TEXT_KEYWORDS]
    X = pd.concat([df[cols], genres], axis=1)

    # red de contención: ninguna numérica debe quedar NaN (los modelos no lo toleran)
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
    print(f"X: {X.shape}  |  y: {None if y is None else y.shape}")
    print("\nGrupos de features:")
    for k, v in feature_groups(X).items():
        print(f"  {k:12s}: {len(v) if isinstance(v, list) else 1}")
    print("\nprimeras columnas:", list(X.columns[:12]))
    Xw, _ = build(WATCHLIST_CSV)
    print(f"\nwatchlist X: {Xw.shape}")
