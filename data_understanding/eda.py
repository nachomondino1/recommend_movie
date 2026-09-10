"""
Análisis exploratorio (EDA) de mis ratings de IMDb.

Uso:
    ./venv/bin/python eda.py

Genera:
    - Resumen numérico por consola
    - Gráficos en outputs/
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # backend sin ventana: solo guarda archivos
import matplotlib.pyplot as plt
import pandas as pd

_ROOT = Path(__file__).resolve().parents[1]
DATA = _ROOT / "data" / "raw" / "ratings.csv"
OUT = _ROOT / "outputs"
OUT.mkdir(exist_ok=True)


def load() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    # Fechas a datetime
    for col in ("Date Rated", "Release Date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # Década de estreno
    df["Decade"] = (df["Year"] // 10 * 10).astype("Int64")
    # Diferencia entre mi nota y la de IMDb (positivo = soy más generoso)
    df["Diff vs IMDb"] = df["Your Rating"] - df["IMDb Rating"]
    return df


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def overview(df: pd.DataFrame) -> None:
    section("FORMA Y COLUMNAS")
    print(f"Filas: {len(df)}  |  Columnas: {df.shape[1]}")
    print("\nValores faltantes por columna:")
    print(df.isna().sum().sort_values(ascending=False))

    section("MI RATING (Your Rating)")
    print(df["Your Rating"].describe())
    print("\nConteo por nota:")
    print(df["Your Rating"].value_counts().sort_index())

    section("YO vs IMDb")
    print(f"Mi promedio:    {df['Your Rating'].mean():.2f}")
    print(f"IMDb promedio:  {df['IMDb Rating'].mean():.2f}")
    print(f"Diferencia media (yo - IMDb): {df['Diff vs IMDb'].mean():+.2f}")
    print(f"Correlación yo vs IMDb: {df['Your Rating'].corr(df['IMDb Rating']):.3f}")

    section("POR TIPO DE TÍTULO")
    print(
        df.groupby("Title Type")["Your Rating"]
        .agg(["count", "mean"])
        .sort_values("count", ascending=False)
        .round(2)
    )

    section("POR DÉCADA DE ESTRENO")
    print(df.groupby("Decade")["Your Rating"].agg(["count", "mean"]).round(2))

    section("POR GÉNERO (un título puede tener varios)")
    g = df.assign(Genre=df["Genres"].str.split(", ")).explode("Genre")
    print(
        g.groupby("Genre")["Your Rating"]
        .agg(["count", "mean"])
        .sort_values("mean", ascending=False)
        .round(2)
    )

    section("CORRELACIÓN CON VARIABLES NUMÉRICAS")
    num = ["IMDb Rating", "Runtime (mins)", "Year", "Num Votes"]
    print(df[["Your Rating"] + num].corr()["Your Rating"].round(3))


def plots(df: pd.DataFrame) -> None:
    # 1. Histograma de mi rating
    fig, ax = plt.subplots(figsize=(7, 4))
    df["Your Rating"].plot.hist(bins=range(1, 12), rwidth=0.9, ax=ax)
    ax.set_title("Distribución de mis notas")
    ax.set_xlabel("Your Rating")
    ax.set_xticks(range(1, 11))
    fig.tight_layout()
    fig.savefig(OUT / "01_hist_rating.png", dpi=120)
    plt.close(fig)

    # 2. Yo vs IMDb
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(df["IMDb Rating"], df["Your Rating"], alpha=0.6)
    lims = [0, 10]
    ax.plot(lims, lims, "--", color="gray", label="y = x")
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.set_xlabel("IMDb Rating")
    ax.set_ylabel("Mi Rating")
    ax.set_title("Mi nota vs nota de IMDb")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "02_scatter_yo_vs_imdb.png", dpi=120)
    plt.close(fig)

    # 3. Promedio de mi nota por género
    g = df.assign(Genre=df["Genres"].str.split(", ")).explode("Genre")
    by_genre = g.groupby("Genre")["Your Rating"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(7, max(4, 0.35 * len(by_genre))))
    by_genre.plot.barh(ax=ax)
    ax.set_title("Mi nota promedio por género")
    ax.set_xlabel("Nota promedio")
    fig.tight_layout()
    fig.savefig(OUT / "03_nota_por_genero.png", dpi=120)
    plt.close(fig)

    print(f"\nGráficos guardados en {OUT}/")


if __name__ == "__main__":
    df = load()
    overview(df)
    plots(df)
