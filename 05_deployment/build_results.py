"""
CRISP-DM · Despliegue: arma los datos de la página web (docs/v3/index.html).

Junta en un solo JSON, que lee el navegador, (1) la descripción de los datos de TMDB (variable respuesta, variables
predictoras y calidad) y (2) los resultados del modelado (`make drivers`, en data/03_modeling/drivers_results.json).
Son solo agregados. La web no recalcula nada: solo dibuja estos números.

    make drivers      # corre prepare_titles.py y drivers_model.py
    make results      # deja docs/v3/data/model_results.json listo para la web
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import json

import numpy as np
import pandas as pd

from config import DOCS, MODELING_DIR, PREP_DIR

OUT = DOCS / "v3" / "data" / "model_results.json"      # la versión 3 vive en docs/v3

# Variables predictoras por grupo: (columnas, qué es, tipo). Las columnas tienen que existir en titles_features.csv;
# si se agrega o saca una variable en prepare_titles.py, build_data_description() avisa en vez de dejar la web vieja.
PREDICTORS = [
    ("Formato", [(["is_tv", "seasons"], "Serie o película, y cantidad de temporadas", "categórica y numérica")]),
    ("Duración y año", [(["runtime", "runtime_missing"], "Minutos (por episodio en series) y una marca si no figuraba", "numérica"),
                        (["year"], "Año de estreno", "numérica")]),
    ("Géneros", [(["g_*"], "Un indicador 0/1 por cada uno de los 18 géneros (los de series se llevan al vocabulario de películas)", "categórica (0/1)"),
                 (["n_genres"], "Cuántos géneros tiene", "numérica")]),
    ("Director", [(["director"], "Nota promedio de los otros títulos del director", "categórica codificada"),
                  (["director_n_titles", "has_director", "n_directors"], "Cuántos títulos tiene en el catálogo, y si figura", "numérica")]),
    ("Elenco", [(["cast_ids"], "Nota promedio de los otros títulos de los 5 primeros del reparto", "lista codificada"),
                (["cast_pop_mean", "cast_pop_max", "cast_n_stars", "cast_titles_mean", "has_credits"], "Popularidad de los actores, cuántos son muy conocidos y cuántos títulos suman", "numérica")]),
    ("Guion, música y fotografía", [(["writers_ids", "composers_ids", "dop_ids"], "Nota promedio de los otros títulos de guionistas, compositor y director de fotografía", "lista codificada")]),
    ("Plataformas", [(["p_*"], "En cuáles de las 12 plataformas más frecuentes está", "categórica (0/1)"),
                     (["n_providers"], "En cuántas plataformas está", "numérica")]),
    ("Sinopsis", [(["overview_len", "has_overview"], "Largo de la sinopsis y si existe", "numérica")]),
]
CIRCULAR = ["votes", "popularity"]       # no entran al análisis principal: dependen de la nota, no la explican


def build_data_description() -> dict:
    t = pd.read_csv(PREP_DIR / "titles_features.csv")
    listed = {c for _, rows in PREDICTORS for cols, _, _ in rows for c in cols if "*" not in c}
    listed |= {c for c in t.columns if c.startswith(("g_", "p_"))}
    known = listed | set(CIRCULAR) | {"tmdb_id", "media_type", "title", "year_raw", "rating", "overview", "writers_ids"}
    missing = sorted(c for c in listed if c not in t.columns)
    extra = sorted(c for c in t.columns if c not in known)
    if missing or extra:
        raise SystemExit(f"El diccionario de variables no coincide con titles_features.csv: faltan {missing}, sobran {extra}")

    r = t["rating"].dropna()
    ok = t[(t["votes"] >= 100) & t["rating"].notna()]
    bins = np.arange(2, 10.5, 0.5)
    counts = np.histogram(ok["rating"], bins=bins)[0].tolist()
    by_type = {k: {"mean": float(g["rating"].mean()), "sd": float(g["rating"].std()), "n": int(len(g))}
               for k, g in ok.groupby("media_type")}
    return {
        "n_total": int(len(t)), "n_movies": int((t.is_tv == 0).sum()), "n_tv": int(t.is_tv.sum()),
        "n_model": int(len(ok)), "min_votes": 100,
        "rating": {"mean": float(ok["rating"].mean()), "sd": float(ok["rating"].std()), "share_ge7": float((ok["rating"] >= 7).mean()),
                   "bins": [float(b) for b in bins[:-1]], "counts": counts, "by_type": by_type},
        "predictors": [{"group": g, "vars": [{"names": cols, "what": what, "kind": kind} for cols, what, kind in rows]}
                       for g, rows in PREDICTORS],
        "coverage": {
            "Duración": float(1 - t["runtime_missing"].mean()), "Director": float(t["has_director"].mean()),
            "Sinopsis": float(t["has_overview"].mean()), "Elenco": float(t["has_credits"].mean()),
        },
    }


def build_drivers() -> dict:
    """Resultados de `make drivers`, solo agregados."""
    d = json.loads((MODELING_DIR / "drivers_results.json").read_text())
    keep = ("n", "n_movies", "n_tv", "min_votes", "rating_mean", "rating_sd", "performance", "importance", "robustness", "raw_by_genre", "actors")
    out = {k: d.get(k) for k in keep}
    out["effects"] = d["effects"][:14]                      # los más grandes (ya vienen ordenados por |efecto|)
    return out


def main() -> None:
    OUT.write_text(json.dumps({"data": build_data_description(), "drivers": build_drivers()}, ensure_ascii=False, indent=1))
    print(f"Guardado: {OUT}")


if __name__ == "__main__":
    main()
