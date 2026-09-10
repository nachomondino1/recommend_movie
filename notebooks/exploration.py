"""
CRISP-DM: Data Understanding - análisis exploratorio (one-off).

    python -m notebooks.exploration

Imprime un resumen y guarda 3 gráficos en outputs/. Las conclusiones están en
docs/2_data_understanding.md; este script se conserva para poder rehacerlas.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import OUTPUTS, RATINGS_CSV


def load() -> pd.DataFrame:
    df = pd.read_csv(RATINGS_CSV)
    for col in ("Date Rated", "Release Date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["Decade"] = (df["Year"] // 10 * 10).astype("Int64")
    df["Diff vs IMDb"] = df["Your Rating"] - df["IMDb Rating"]
    return df


def _section(title: str) -> None:
    print("\n" + "=" * 60 + f"\n{title}\n" + "=" * 60)


def summary(df: pd.DataFrame) -> None:
    _section("FORMA Y FALTANTES")
    print(f"Filas: {len(df)}  |  Columnas: {df.shape[1]}")
    print(df.isna().sum().sort_values(ascending=False).head(6))

    _section("MI RATING")
    print(df["Your Rating"].describe())
    print(df["Your Rating"].value_counts().sort_index())

    _section("YO vs IMDb")
    print(f"Mi promedio {df['Your Rating'].mean():.2f}  |  IMDb {df['IMDb Rating'].mean():.2f}")
    print(f"Diferencia media (yo - IMDb): {df['Diff vs IMDb'].mean():+.2f}")
    print(f"Correlación: {df['Your Rating'].corr(df['IMDb Rating']):.3f}")

    _section("POR GÉNERO")
    g = df.assign(Genre=df["Genres"].str.split(", ")).explode("Genre")
    print(g.groupby("Genre")["Your Rating"].agg(["count", "mean"])
          .sort_values("mean", ascending=False).round(2))

    _section("CORRELACIÓN CON NUMÉRICAS")
    num = ["IMDb Rating", "Runtime (mins)", "Year", "Num Votes"]
    print(df[["Your Rating"] + num].corr()["Your Rating"].round(3))


def plots(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    df["Your Rating"].plot.hist(bins=range(1, 12), rwidth=0.9, ax=ax)
    ax.set(title="Distribución de mis notas", xlabel="Your Rating")
    ax.set_xticks(range(1, 11))
    fig.tight_layout(); fig.savefig(OUTPUTS / "01_hist_rating.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(df["IMDb Rating"], df["Your Rating"], alpha=0.6)
    ax.plot([0, 10], [0, 10], "--", color="gray", label="y = x")
    ax.set(xlim=(0, 10), ylim=(0, 10), xlabel="IMDb Rating", ylabel="Mi Rating",
           title="Mi nota vs IMDb")
    ax.legend()
    fig.tight_layout(); fig.savefig(OUTPUTS / "02_scatter_yo_vs_imdb.png", dpi=120); plt.close(fig)

    g = df.assign(Genre=df["Genres"].str.split(", ")).explode("Genre")
    by_genre = g.groupby("Genre")["Your Rating"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(7, max(4, 0.35 * len(by_genre))))
    by_genre.plot.barh(ax=ax)
    ax.set(title="Mi nota promedio por género", xlabel="Nota promedio")
    fig.tight_layout(); fig.savefig(OUTPUTS / "03_nota_por_genero.png", dpi=120); plt.close(fig)

    print(f"\nGráficos en {OUTPUTS}/")


if __name__ == "__main__":
    d = load()
    summary(d)
    plots(d)
