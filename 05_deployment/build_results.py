"""
CRISP-DM · Despliegue: arma los datos de la portada de la web (docs/index.html, el proyecto).

Junta en un solo JSON, que lee el navegador, (1) los resultados de la prueba de robustez (los escribe
`make robust` en data/03_modeling/) y (2) la descripción de los datos: la variable respuesta y las variables
predictoras con su fuente. Son solo agregados, sin títulos ni datos personales. La web no recalcula nada:
solo dibuja estos números.

    make results      # después de `make robust`
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import json

import numpy as np
import pandas as pd

from config import DOCS, MODELING_DIR, RATINGS_CSV, TMDB_CSV
from features import build

OUT = DOCS / "data" / "model_results.json"

# Diccionario de variables predictoras: grupo -> [(columnas, qué es, tipo)]. Las columnas tienen que ser
# EXACTAMENTE las de features.build(); si se agrega o saca una variable, build_data_description() avisa.
PREDICTORS = {
    "De IMDb (tu archivo de notas)": [
        (["IMDb Rating"], "Nota de IMDb del título (si falta, la de TMDB)", "numérica"),
        (["Year"], "Año de estreno", "numérica"),
        (["Runtime (mins)", "runtime_missing"], "Duración en minutos, y una marca si no figuraba", "numérica"),
        (["log_votes"], "Cantidad de votos en IMDb (en escala logarítmica)", "numérica"),
        (["Title Type"], "Película o serie", "categórica"),
        (["n_genres"], "Cuántos géneros tiene", "numérica"),
        (["genre_*"], "Un indicador 0/1 por género (22 géneros)", "categórica (0/1)"),
        (["years_since_release"], "Años entre el estreno y el día que lo puntuaste", "numérica"),
        (["is_franchise"], "Si el nombre parece de una secuela (número, parte, volumen)", "categórica (0/1)"),
    ],
    "De TMDB (API)": [
        (["tmdb_vote_average", "log_tmdb_votes"], "Nota y cantidad de votos en TMDB", "numérica"),
        (["tmdb_popularity"], "Popularidad en TMDB", "numérica"),
        (["log_budget"], "Presupuesto (en escala logarítmica)", "numérica"),
        (["n_seasons", "n_episodes"], "Temporadas y episodios (solo series)", "numérica"),
        (["media_type"], "Película o serie según TMDB", "categórica"),
        (["lang_grouped"], "Idioma original (los 4 más frecuentes y \"otro\")", "categórica"),
        (["director"], "Director o creador", "categórica"),
        (["overview"], "Sinopsis", "texto"),
        (["keywords_txt"], "Palabras clave de TMDB", "texto"),
    ],
}


def build_data_description() -> dict:
    """Describe los datos de entrenamiento: variable respuesta, variables predictoras y calidad."""
    X, y = build()
    y = y.to_numpy(float)
    listed = {c for rows in PREDICTORS.values() for cols, _, _ in rows for c in cols if "*" not in c}
    listed |= {c for c in X.columns if c.startswith("genre_")}
    missing, extra = set(X.columns) - listed, listed - set(X.columns)
    if missing or extra:
        raise SystemExit(f"El diccionario de variables no coincide con features.build(): faltan {sorted(missing)}, sobran {sorted(extra)}")

    ratings = pd.read_csv(RATINGS_CSV).dropna(subset=["Your Rating", "IMDb Rating"])
    dev = (ratings["Your Rating"] - ratings["IMDb Rating"]).to_numpy(float)
    tmdb = pd.read_csv(TMDB_CSV)
    cover = {col: int((tmdb[col].fillna("").astype(str).str.len() > 0).sum()) for col in ("overview", "keywords", "cast_top", "director")}
    return {
        "n_rows": int(len(y)), "n_predictors": int(X.shape[1]),
        "response": {
            "name": "Your Rating", "mean": float(y.mean()), "median": float(np.median(y)), "sd": float(y.std()),
            "counts": [int((y == k).sum()) for k in range(1, 11)],
            "liked": int((y >= 7).sum()),
            "deviation": {"mean": float(dev.mean()), "sd": float(dev.std()), "n": int(len(dev))},
        },
        "predictors": [{"group": g, "vars": [{"names": cols, "what": what, "kind": kind} for cols, what, kind in rows]}
                       for g, rows in PREDICTORS.items()],
        "tmdb_rows": int(len(tmdb)), "tmdb_coverage": cover,
    }


def main() -> None:
    comp = pd.read_csv(MODELING_DIR / "robustness_comparison.csv")
    curve = pd.read_csv(MODELING_DIR / "robustness_learning_curve.csv")
    lc = {name: {"sizes": g["n_train"].tolist(), "mean": g["mae"].tolist(), "se": g["se"].tolist()}
          for name, g in curve.groupby("modelo", sort=False)}
    # NaN (la fila de la base no tiene diferencias contra sí misma) no es JSON válido: va como null
    comp_rows = json.loads(comp.to_json(orient="records", force_ascii=False))
    OUT.write_text(json.dumps({"comp": comp_rows, "lc": lc, "data": build_data_description()}, ensure_ascii=False, indent=1))
    print(f"Guardado: {OUT}  ({len(comp_rows)} modelos, {len(lc)} curvas)")


if __name__ == "__main__":
    main()
