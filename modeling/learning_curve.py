"""
Fase Modeling - curva de aprendizaje.

Responde: ¿cuánto mejoraría el modelo si tuviera más ratings?
Entrena con subconjuntos crecientes de los 126 títulos y mide el rendimiento
de validación cruzada en cada tamaño.

Truco para la regresión: como pred_nota = IMDb + desvío_predicho, el error
absoluto sobre el desvío es idéntico al error sobre la nota. Así que entrenamos
con target = desvío y medimos MAE directamente.

Uso:
    ./venv/bin/python modeling/learning_curve.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.model_selection import StratifiedKFold, learning_curve
from sklearn.pipeline import Pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import OUTPUTS
from data_preparation.build_features import build, feature_groups
from modeling.train import make_preprocessor

SIZES = np.linspace(0.25, 1.0, 8)


def curve(estimator, X, y, scoring, cv):
    n, train, test = learning_curve(
        estimator, X, y, train_sizes=SIZES, cv=cv, scoring=scoring,
        shuffle=True, random_state=42,
    )
    return n, -test.mean(axis=1) if scoring.startswith("neg_") else test.mean(axis=1), \
        test.std(axis=1)


def main() -> None:
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = (y >= 7).astype(int)

    reg = Pipeline([("pre", make_preprocessor(groups, "continuous")),
                    ("m", RandomForestRegressor(n_estimators=400, random_state=42))])
    clf = Pipeline([("pre", make_preprocessor(groups, "binary")),
                    ("m", GradientBoostingClassifier(random_state=42))])

    n1, mae, mae_sd = curve(reg, X, resid, "neg_mean_absolute_error",
                            cv=5)
    n2, auc, auc_sd = curve(clf, X, like, "roc_auc",
                            cv=StratifiedKFold(5, shuffle=True, random_state=42))

    print("REGRESIÓN (MAE de la nota, más bajo mejor) — baseline ~1.31")
    for a, b in zip(n1, mae):
        print(f"  n={a:3d}  MAE={b:.3f}")
    print("\nBINARIO (ROC AUC, más alto mejor) — baseline 0.50")
    for a, b in zip(n2, auc):
        print(f"  n={a:3d}  AUC={b:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(n1, mae, "o-", color="tab:red")
    ax1.fill_between(n1, mae - mae_sd, mae + mae_sd, alpha=0.15, color="tab:red")
    ax1.axhline(1.31, ls="--", color="gray", label="baseline (media)")
    ax1.set_title("Regresión: MAE de la nota vs tamaño de entrenamiento")
    ax1.set_xlabel("N° de títulos de entrenamiento")
    ax1.set_ylabel("MAE (validación cruzada)")
    ax1.legend()

    ax2.plot(n2, auc, "o-", color="tab:blue")
    ax2.fill_between(n2, auc - auc_sd, auc + auc_sd, alpha=0.15, color="tab:blue")
    ax2.axhline(0.5, ls="--", color="gray", label="azar")
    ax2.axhline(0.65, ls=":", color="green", label="objetivo mínimo")
    ax2.set_title("Binario ≥7: ROC AUC vs tamaño de entrenamiento")
    ax2.set_xlabel("N° de títulos de entrenamiento")
    ax2.set_ylabel("ROC AUC (validación cruzada)")
    ax2.legend()

    fig.tight_layout()
    dest = OUTPUTS / "learning_curve.png"
    fig.savefig(dest, dpi=120)
    print(f"\nGráfico: {dest}")


if __name__ == "__main__":
    main()
