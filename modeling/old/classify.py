"""
Paso 3A: reformular el problema como clasificación binaria.

    y = 1  si Your Rating >= THRESHOLD   ("la disfruto")
    y = 0  si Your Rating <  THRESHOLD

Uso:
    ./venv/bin/python classify.py           # umbral 6
    ./venv/bin/python classify.py 7         # umbral 7

Compara modelos con validación cruzada estratificada 5-fold.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline

from model import build_features, make_preprocessor

DATA = Path(__file__).resolve().parents[2] / "data" / "raw" / "ratings.csv"


def evaluate(name, pipe, X, y, cv):
    pred = cross_val_predict(pipe, X, y, cv=cv)
    proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    return {
        "modelo": name,
        "accuracy": (pred == y).mean(),
        "balanced_acc": balanced_accuracy_score(y, pred),
        "roc_auc": roc_auc_score(y, proba),
    }


def main() -> None:
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 6

    df = pd.read_csv(DATA)
    X, _ = build_features(df)
    y = (df["Your Rating"] >= threshold).astype(int)

    genre_cols = [c for c in X.columns if c.startswith("genre_")]
    pre = make_preprocessor(genre_cols)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    pos_rate = y.mean()
    print(f"\nUmbral: nota >= {threshold}")
    print(f"Filas: {len(X)}  |  Positivos (la disfruto): {y.sum()} ({pos_rate:.1%})")
    print(f"Baseline (predecir siempre la clase mayoritaria): {max(pos_rate, 1 - pos_rate):.1%}\n")

    models = {
        "Baseline": DummyClassifier(strategy="most_frequent"),
        "LogReg": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, random_state=42, class_weight="balanced"
        ),
        "KNN (k=7)": KNeighborsClassifier(n_neighbors=7),
    }

    rows = []
    for name, est in models.items():
        pipe = Pipeline([("pre", pre), ("model", est)])
        rows.append(evaluate(name, pipe, X, y, cv))

    res = pd.DataFrame(rows).set_index("modelo").round(3)
    print(res.to_string())

    # Matriz de confusión del mejor por ROC AUC (excluyendo baseline)
    best = res.drop("Baseline")["roc_auc"].idxmax()
    pipe = Pipeline([("pre", pre), ("model", models[best])])
    pred = cross_val_predict(pipe, X, y, cv=cv)
    cm = confusion_matrix(y, pred)
    print(f"\nMatriz de confusión — {best} (filas = real, columnas = predicho):")
    print(pd.DataFrame(cm, index=["real 0", "real 1"], columns=["pred 0", "pred 1"]))
    print("\nroc_auc = 0.5 es azar, 1.0 es perfecto. balanced_acc corrige el desbalance.")


if __name__ == "__main__":
    main()
