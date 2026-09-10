"""
Fase Modeling - entrenar los modelos finales con TODOS los ratings y guardarlos.

Genera en models/:
    regressor.joblib   - Pipeline que predice el DESVÍO vs IMDb
    classifier.joblib  - Pipeline que predice P(Your Rating >= 7)
    meta.json          - fecha, n de entrenamiento, scores de CV, hash de features

Uso:
    ./venv/bin/python modeling/fit_final.py

Volvé a correrlo cada vez que cambie data/raw/ratings.csv.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import RATINGS_CSV, ROOT
from data_preparation.build_features import build, feature_groups
from modeling.pipeline import LIKE_THRESHOLD, build_classifier, build_regressor

MODELS = ROOT / "models"


def main() -> None:
    MODELS.mkdir(exist_ok=True)
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = (y >= LIKE_THRESHOLD).astype(int)

    reg = build_regressor(groups)
    clf = build_classifier(groups)

    # scores de CV (para dejar registro en meta.json)
    kf = KFold(5, shuffle=True, random_state=42)
    skf = StratifiedKFold(5, shuffle=True, random_state=42)
    cv_mae = mean_absolute_error(y, imdb + cross_val_predict(reg, X, resid, cv=kf))
    cv_auc = roc_auc_score(like, cross_val_predict(clf, X, like, cv=skf, method="predict_proba")[:, 1])

    reg.fit(X, resid)
    clf.fit(X, like)

    joblib.dump(reg, MODELS / "regressor.joblib")
    joblib.dump(clf, MODELS / "classifier.joblib")

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_train": int(len(X)),
        "ratings_csv_mtime": RATINGS_CSV.stat().st_mtime,
        "like_threshold": LIKE_THRESHOLD,
        "cv_mae_rating": round(float(cv_mae), 3),
        "cv_roc_auc_like": round(float(cv_auc), 3),
        "feature_columns": list(X.columns),
    }
    (MODELS / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"Guardado en {MODELS}/")
    print(f"  n_train={meta['n_train']}  CV MAE={meta['cv_mae_rating']}  "
          f"CV AUC={meta['cv_roc_auc_like']}")


if __name__ == "__main__":
    main()
