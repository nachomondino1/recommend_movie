"""
CRISP-DM: Deployment - análisis del patrón de gusto del usuario.

A diferencia de model.py/dashboard.py, esto no predice nada: solo resume lo que
el usuario ya puntuó (data/ratings.csv) - cuántos títulos, con qué notas, qué
géneros/directores/décadas prefiere. Sin métricas de modelo (MAE/AUC).

    from src.taste import build_taste_stats
"""

import pandas as pd

from src.config import RATINGS_CSV
from src.data import tmdb_table

MIN_GENRE_N = 3
MIN_DIRECTOR_N = 2
TOP_DIRECTORS = 8
TOP_TITLES = 5


def _group_avg(df: pd.DataFrame, col: str, sep: str | None, min_n: int) -> list[dict]:
    if sep:
        exploded = df.assign(**{col: df[col].fillna("").str.split(sep)}).explode(col)
        exploded[col] = exploded[col].str.strip()
        exploded = exploded[exploded[col] != ""]
    else:
        exploded = df[df[col].fillna("") != ""]
    g = exploded.groupby(col)["Your Rating"].agg(n="count", avg="mean")
    g = g[g["n"] >= min_n].sort_values("avg", ascending=False)
    return [{"label": label, "n": int(row["n"]), "avg": round(row["avg"], 2)}
            for label, row in g.iterrows()]


def _title_cards(df: pd.DataFrame, ascending: bool) -> list[dict]:
    cols = ["Title", "Your Rating", "IMDb Rating", "Year", "Genres", "poster_path", "URL"]
    picked = df.sort_values("Your Rating", ascending=ascending).head(TOP_TITLES)
    return picked[cols].to_dict("records")


def build_taste_stats() -> dict:
    df = pd.read_csv(RATINGS_CSV)
    df = df.merge(tmdb_table()[["imdb_id", "poster_path", "director"]],
                  left_on="Const", right_on="imdb_id", how="left")
    df["Directors"] = df["Directors"].fillna(df["director"])
    df["type_label"] = df["Title Type"].where(df["Title Type"] == "Movie", "Serie")
    df["decade"] = (df["Year"] // 10 * 10).astype("Int64").astype(str) + "s"

    rating_counts = (df["Your Rating"].value_counts()
                     .reindex(range(1, 11), fill_value=0).tolist())

    by_decade = (df.groupby("decade")["Your Rating"].agg(n="count", avg="mean")
                 .reset_index().sort_values("decade"))
    by_decade["avg"] = by_decade["avg"].round(2)

    return {
        "n_rated": len(df),
        "n_movies": int((df["Title Type"] == "Movie").sum()),
        "n_series": int((df["Title Type"] != "Movie").sum()),
        "mean_rating": round(df["Your Rating"].mean(), 2),
        "median_rating": float(df["Your Rating"].median()),
        "deviation_vs_imdb": round((df["Your Rating"] - df["IMDb Rating"]).mean(), 2),
        "rating_counts": rating_counts,
        "by_type": _group_avg(df, "type_label", sep=None, min_n=1),
        "by_genre": _group_avg(df, "Genres", sep=", ", min_n=MIN_GENRE_N),
        "by_director": _group_avg(df, "Directors", sep=None, min_n=MIN_DIRECTOR_N)[:TOP_DIRECTORS],
        "by_decade": by_decade.to_dict("records"),
        "top": _title_cards(df, ascending=False),
        "bottom": _title_cards(df, ascending=True),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_taste_stats(), indent=2, ensure_ascii=False))
