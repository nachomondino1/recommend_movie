"""
Fase Deployment - aplicar el modelo a la watchlist.

Carga los modelos guardados en models/ (los entrena si no existen) y predice,
para cada título de la watchlist:
    - pred_rating : nota estimada (IMDb Rating + desvío predicho, RandomForest)
    - p_like      : probabilidad estimada de que le pongas >= 7 (GradientBoosting)

Salida: outputs/watchlist_scored.csv, ordenada por pred_rating desc.

Uso:
    ./venv/bin/python deployment/predict_watchlist.py
"""

import runpy
import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import OUTPUTS, RATINGS_CSV, ROOT, WATCHLIST_CSV
from data_preparation.build_features import build

MODELS = ROOT / "models"
REG_PATH = MODELS / "regressor.joblib"
CLF_PATH = MODELS / "classifier.joblib"


def _fit_final() -> None:
    print(">> Entrenando modelos finales (modeling/fit_final.py)...")
    runpy.run_path(str(ROOT / "modeling" / "fit_final.py"), run_name="__main__")


def load_models():
    if not REG_PATH.exists() or not CLF_PATH.exists():
        _fit_final()
    elif RATINGS_CSV.stat().st_mtime > REG_PATH.stat().st_mtime:
        print("!! ratings.csv es más nuevo que el modelo guardado -> re-entreno.")
        _fit_final()
    return joblib.load(REG_PATH), joblib.load(CLF_PATH)


def main() -> None:
    reg, clf = load_models()

    X_tr, _ = build()  # sólo para alinear columnas
    X_wl, _ = build(WATCHLIST_CSV)
    X_wl = X_wl.reindex(columns=X_tr.columns, fill_value=0)

    wl = pd.read_csv(WATCHLIST_CSV)
    wl["pred_rating"] = (X_wl["IMDb Rating"].to_numpy() + reg.predict(X_wl)).clip(1, 10)
    wl["p_like"] = clf.predict_proba(X_wl)[:, 1]
    wl["Directors"] = wl["Directors"].fillna("")

    out_cols = ["Title", "Year", "Title Type", "IMDb Rating", "Directors", "Genres",
                "pred_rating", "p_like"]
    result = (wl[out_cols].sort_values("pred_rating", ascending=False)
              .round({"pred_rating": 1, "p_like": 2}).reset_index(drop=True))

    dest = OUTPUTS / "watchlist_scored.csv"
    result.to_csv(dest, index=False)
    print(f"\nGuardado: {dest}  ({len(result)} títulos)\n")
    print("TOP 15 recomendados:")
    print(result.head(15).to_string())
    print("\nBOTTOM 5 (mejor saltear):")
    print(result.tail(5).to_string())
    print("\nNota: MAE del modelo ~1.26 y AUC ~0.63. Tomar como orden sugerido, "
          "no como veredicto.")


if __name__ == "__main__":
    main()
