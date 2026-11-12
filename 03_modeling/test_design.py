"""
CRISP-DM · Modelado · 1/3 «Generate test design» (cómo vamos a juzgar un modelo).

Acá vive TODO lo que define qué es "un buen resultado", para que entrenar (build_model.py)
y comparar (assess_model.py) usen exactamente las mismas reglas:

  - el objetivo "me gustó"  (nota >= LIKE_THRESHOLD)
  - cómo se parten los datos para validar (CV de 5 folds, sembrada; repetida para las pruebas duras)
  - las bases contra las que hay que ganar (tu promedio; la nota de IMDb cruda y CALIBRADA a tu escala)
  - las métricas (MAE, RMSE, Spearman, AUC) y el bootstrap pareado para compararlas con intervalos

No se corre solo: lo importan los otros dos archivos.
"""

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold

# --- objetivo y semillas ----------------------------------------------------------------------
LIKE_THRESHOLD = 7        # "te gustó" = nota >= 7
SEED = 42                 # validación estándar (build_model.py y la comparación de assess_model.py)
N_FOLDS = 5
ROBUST_SEED = 7           # prueba de robustez (assess_model.py --robust)
ROBUST_REPEATS = 10       # repeticiones de la CV de 5 folds
N_BOOT = 5000             # remuestreos del bootstrap pareado


def like_labels(y):
    return (np.asarray(y) >= LIKE_THRESHOLD).astype(int)


def regression_cv(seed: int = SEED) -> KFold:
    return KFold(N_FOLDS, shuffle=True, random_state=seed)


def classification_cv(seed: int = SEED) -> StratifiedKFold:
    return StratifiedKFold(N_FOLDS, shuffle=True, random_state=seed)


# --- bases (lo que hay que superar) -----------------------------------------------------------
def calibrate_imdb(imdb_train, y_train, imdb_test):
    """La base JUSTA: la nota de IMDb reescalada a tu forma de puntuar (a + b·IMDb), ajustada solo
    con el train. La nota de IMDb "tal cual" pierde por una razón tonta: vos puntuás más bajo."""
    b, a = np.polyfit(np.asarray(imdb_train, float), np.asarray(y_train, float), 1)
    return a + b * np.asarray(imdb_test, float)


# --- métricas ---------------------------------------------------------------------------------
def score_predictions(pred, y, like=None) -> dict:
    """MAE/RMSE (menor es mejor) y Spearman/AUC(>=7) (mayor es mejor)."""
    pred, y = np.asarray(pred, float), np.asarray(y, float)
    like = like_labels(y) if like is None else like
    err = np.abs(pred - y)
    return {"MAE": err.mean(), "RMSE": np.sqrt(((pred - y) ** 2).mean()),
            "±1": (err <= 1).mean(), "Spearman": spearmanr(pred, y)[0],
            "AUC(>=7)": roc_auc_score(like, pred)}


def paired_bootstrap(model_pred, base_pred, y, like, rng):
    """Diferencia (modelo − base) de MAE y de AUC remuestreando títulos. Devuelve (d_mae, d_auc);
    si el IC 95 % de d_mae no excluye el cero, no hay evidencia de que el modelo le gane a la base."""
    y, like = np.asarray(y, float), np.asarray(like)
    n = len(y)
    em, eb = np.abs(model_pred - y), np.abs(base_pred - y)
    d_mae, d_auc = [], []
    for _ in range(N_BOOT):
        i = rng.integers(0, n, n)
        d_mae.append(em[i].mean() - eb[i].mean())
        if 0 < like[i].sum() < n:
            d_auc.append(roc_auc_score(like[i], model_pred[i]) - roc_auc_score(like[i], base_pred[i]))
    return np.array(d_mae), np.array(d_auc)


def ci95(a):
    return np.percentile(a, [2.5, 97.5])
