"""
Fase Deployment - aplicar el modelo a la watchlist.

Entrena con los 126 títulos puntuados y predice, para cada título de la
watchlist:
    - pred_rating : nota estimada (IMDb Rating + desvío predicho por RandomForest)
    - p_like      : probabilidad estimada de que le pongas >= 7 (GradientBoosting)

Salida: outputs/watchlist_scored.csv, ordenada por pred_rating desc.

Uso:
    ./venv/bin/python deployment/predict_watchlist.py
"""

import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import OUTPUTS, WATCHLIST_CSV
from data_preparation.build_features import build, feature_groups
from modeling.train import make_preprocessor


def main() -> None:
    X_tr, y = build()
    groups = feature_groups(X_tr)
    imdb_tr = X_tr["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb_tr
    like = (y >= 7).astype(int)

    X_wl, _ = build(WATCHLIST_CSV)
    X_wl = X_wl.reindex(columns=X_tr.columns, fill_value=0)  # alinear columnas

    reg = Pipeline([
        ("pre", make_preprocessor(groups, target_type="continuous")),
        ("m", RandomForestRegressor(n_estimators=400, random_state=42)),
    ]).fit(X_tr, resid)

    clf = Pipeline([
        ("pre", make_preprocessor(groups, target_type="binary")),
        ("m", GradientBoostingClassifier(random_state=42)),
    ]).fit(X_tr, like)

    wl = pd.read_csv(WATCHLIST_CSV)
    wl["pred_rating"] = (X_wl["IMDb Rating"].to_numpy() + reg.predict(X_wl)).clip(1, 10)
    wl["p_like"] = clf.predict_proba(X_wl)[:, 1]

    out_cols = ["Title", "Year", "Title Type", "IMDb Rating", "Genres",
                "pred_rating", "p_like"]
    result = (wl[out_cols].sort_values("pred_rating", ascending=False)
              .round({"pred_rating": 1, "p_like": 2}).reset_index(drop=True))

    dest = OUTPUTS / "watchlist_scored.csv"
    result.to_csv(dest, index=False)
    print(f"Guardado: {dest}  ({len(result)} títulos)\n")
    print("TOP 15 recomendados:")
    print(result.head(15).to_string())
    print("\nBOTTOM 5 (mejor saltear):")
    print(result.tail(5).to_string())
    print("\nNota: MAE del modelo ~1.26 y AUC ~0.63. Tomar como orden sugerido, "
          "no como veredicto.")


if __name__ == "__main__":
    main()
