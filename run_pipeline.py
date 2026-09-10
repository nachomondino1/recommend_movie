"""
Corre todo el pipeline de punta a punta.

Pensado para después de re-exportar un ratings.csv más grande desde IMDb:
sólo hay que reemplazar data/raw/ratings.csv y correr este script.

    ./venv/bin/python run_pipeline.py
    ./venv/bin/python run_pipeline.py --skip-tmdb   # si no cambió la watchlist
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

STEPS = [
    ("Data Understanding - EDA", "data_understanding/eda.py"),
    ("Data Preparation - enriquecer con TMDB", "data_preparation/enrich_tmdb.py"),
    ("Modeling - comparar modelos (CV)", "modeling/train.py"),
    ("Modeling - curva de aprendizaje", "modeling/learning_curve.py"),
    ("Modeling - entrenar y guardar modelo final", "modeling/fit_final.py"),
    ("Deployment - puntuar watchlist", "deployment/predict_watchlist.py"),
    ("Deployment - dashboard HTML", "deployment/build_dashboard.py"),
]


def main() -> None:
    skip_tmdb = "--skip-tmdb" in sys.argv
    for title, script in STEPS:
        if skip_tmdb and "enrich_tmdb" in script:
            print(f"\n===== {title}  [SALTEADO] =====")
            continue
        print(f"\n===== {title} =====", flush=True)
        r = subprocess.run([PY, str(ROOT / script)], cwd=ROOT)
        if r.returncode != 0:
            print(f"\n!! Falló: {script}", file=sys.stderr)
            sys.exit(r.returncode)
    print("\n===== Pipeline completo. Revisá outputs/ =====")


if __name__ == "__main__":
    main()
