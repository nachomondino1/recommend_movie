"""
CRISP-DM: Evaluación - diagnósticos del modelo y de las reseñas.

    python 04_evaluation/evaluate.py     # comparación de modelos (CV), curva de aprendizaje,
                                         # trayectoria real de scores e insights de reseñas

Entrenar y puntuar vive en 03_modeling/model.py; `make eval` corre primero eso y después esto.
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import re
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict, learning_curve
from sklearn.pipeline import Pipeline

from config import METRICS_CSV, OUTPUTS
from features import build, feature_groups
from pipeline import LIKE_THRESHOLD, build_classifier, build_regressor, make_preprocessor
from tmdb_data import load_reviews

# --------------------------------------------------------------------------- #
# Diagnósticos
# --------------------------------------------------------------------------- #
def compare_models() -> None:
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    kf = KFold(5, shuffle=True, random_state=42)

    rows = []

    def rec(name, pred):
        err = np.abs(pred - y)
        rows.append({"modelo": name, "MAE": err.mean(),
                     "RMSE": np.sqrt(((pred - y) ** 2).mean()), "±1": (err <= 1).mean()})

    rec("Baseline: media de tu nota", np.full(len(y), y.mean()))
    rec("Regla fija: IMDb + media(desvío)", imdb + resid.mean())
    for name, est in {"Ridge (nota directa)": Ridge(alpha=3.0),
                      "RandomForest (nota directa)": RandomForestRegressor(400, random_state=42)}.items():
        rec(name, cross_val_predict(Pipeline([("pre", make_preprocessor(groups, "continuous")),
                                              ("m", est)]), X, y, cv=kf))
    for name, est in {"Ridge (desvío)": Ridge(alpha=3.0),
                      "RandomForest (desvío)": RandomForestRegressor(400, random_state=42)}.items():
        pr = cross_val_predict(Pipeline([("pre", make_preprocessor(groups, "continuous")),
                                         ("m", est)]), X, resid, cv=kf)
        rec(name, imdb + pr)
    print("\n--- REGRESIÓN ---")
    print(pd.DataFrame(rows).set_index("modelo").round(3).to_string())

    like = (y >= LIKE_THRESHOLD).astype(int)
    skf = StratifiedKFold(5, shuffle=True, random_state=42)
    brows = []
    for name, est in {"Baseline": DummyClassifier(strategy="most_frequent"),
                      "LogReg": LogisticRegression(C=0.3, max_iter=2000, class_weight="balanced"),
                      "GradientBoosting": GradientBoostingClassifier(random_state=42)}.items():
        pipe = Pipeline([("pre", make_preprocessor(groups, "binary")), ("m", est)])
        pred = cross_val_predict(pipe, X, like, cv=skf)
        proba = cross_val_predict(pipe, X, like, cv=skf, method="predict_proba")[:, 1]
        brows.append({"modelo": name, "accuracy": (pred == like).mean(),
                      "balanced_acc": balanced_accuracy_score(like, pred),
                      "roc_auc": roc_auc_score(like, proba)})
    print(f"\n--- BINARIO (>= {LIKE_THRESHOLD})  positivos {like.sum()}/{len(like)} "
          f"({like.mean():.0%}) ---")
    print(pd.DataFrame(brows).set_index("modelo").round(3).to_string())


def learning_curve_report() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = (y >= LIKE_THRESHOLD).astype(int)
    sizes = np.linspace(0.25, 1.0, 8)

    n1, _, te1 = learning_curve(build_regressor(groups), X, resid, train_sizes=sizes, cv=5,
                                scoring="neg_mean_absolute_error", shuffle=True, random_state=42)
    n2, _, te2 = learning_curve(build_classifier(groups), X, like, train_sizes=sizes,
                                cv=StratifiedKFold(5, shuffle=True, random_state=42),
                                scoring="roc_auc", shuffle=True, random_state=42)
    mae, auc = -te1.mean(axis=1), te2.mean(axis=1)

    print("\n--- CURVA DE APRENDIZAJE ---")
    print("  n  | MAE  | AUC")
    for a, m, u in zip(n1, mae, auc):
        print(f"  {a:3d} | {m:.3f} | {u:.3f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax1.plot(n1, mae, "o-", color="tab:red"); ax1.axhline(1.31, ls="--", color="gray")
    ax1.set(title="MAE de la nota vs n entrenamiento", xlabel="n", ylabel="MAE (CV)")
    ax2.plot(n2, auc, "o-", color="tab:blue"); ax2.axhline(0.5, ls="--", color="gray")
    ax2.axhline(0.65, ls=":", color="green")
    ax2.set(title="ROC AUC (>=7) vs n entrenamiento", xlabel="n", ylabel="AUC (CV)")
    fig.tight_layout()
    fig.savefig(OUTPUTS / "learning_curve.png", dpi=120)
    print(f"Gráfico: {OUTPUTS / 'learning_curve.png'}")


def plot_history() -> None:
    """Trayectoria REAL de los scores CV según fue creciendo ratings.csv
    (metrics_history.csv). Distinta de la curva de aprendizaje, que es simulada."""
    if not METRICS_CSV.exists():
        return
    hist = pd.read_csv(METRICS_CSV)
    if len(hist) < 2:
        print(f"\n(metrics_history.csv tiene {len(hist)} punto; hacen falta ≥2 para el gráfico)")
        return

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(8, 4.5))
    ax2 = ax1.twinx()
    ax1.plot(hist["n_train"], hist["cv_mae_rating"], "o-", color="tab:red", label="MAE")
    ax2.plot(hist["n_train"], hist["cv_roc_auc_like"], "s-", color="tab:blue", label="AUC")
    ax1.set(xlabel="ratings en el dataset", ylabel="MAE (CV)", title="Trayectoria real de los scores")
    ax2.set_ylabel("ROC AUC (CV)")
    ax1.legend(loc="upper left"); ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(OUTPUTS / "metrics_history.png", dpi=120)
    print(f"\n--- TRAYECTORIA REAL ({len(hist)} puntos) ---")
    print(hist.to_string(index=False))
    print(f"Gráfico: {OUTPUTS / 'metrics_history.png'}")


# Spanish stopwords para el análisis de reseñas -- no exhaustivo, alcanza para
# filtrar conectores comunes de un texto corto e informal.
_STOPWORDS = {
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "más", "pero",
    "sus", "le", "ya", "este", "porque", "esta", "entre", "cuando", "muy",
    "sin", "sobre", "también", "hasta", "hay", "donde", "quien", "desde",
    "todo", "nos", "durante", "todos", "uno", "les", "esa", "eso", "ese",
    "ante", "ellos", "esto", "antes", "algunos", "unos", "otro", "otras",
    "otra", "tanto", "estos", "mucho", "quienes", "nada", "muchos", "cual",
    "poco", "ella", "estar", "estas", "algunas", "algo", "nosotros", "ellas",
    "esos", "esas", "estoy", "estás", "está", "estamos", "están", "tiene",
    "tienen", "hace", "hacer", "había", "soy", "eres", "así", "cada", "vez",
    "bien", "mal", "creo", "pienso", "capitulos", "capítulos", "personaje",
    "mucha", "muchas", "cosas", "cosa",
}


def _review_words(text: str) -> list[str]:
    tokens = re.findall(r"[a-zñáéíóúü]+", str(text).lower())
    return [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]


def review_insights() -> None:
    """Analiza data/reviews.csv: qué palabras aparecen más en la parte 'me gustó'
    vs 'no me gustó', juntando todas tus reseñas. Es un insight para vos -- NO
    entra como feature del modelo, porque no existe reseña para un título que
    todavía no viste."""
    reviews = load_reviews()
    if reviews.empty:
        print("\n(sin reseñas todavía -- 'make review TITLE=\"X\" LIKED=\"...\" DISLIKED=\"...\"')")
        return

    liked = reviews["Liked"].dropna()
    disliked = reviews["Disliked"].dropna()
    print(f"\n--- RESEÑAS ({len(reviews)} títulos reseñados; {len(liked)} con sección "
          f"'me gustó', {len(disliked)} con 'no me gustó') ---")

    liked_words = Counter(w for t in liked for w in _review_words(t))
    disliked_words = Counter(w for t in disliked for w in _review_words(t))
    if not liked_words and not disliked_words:
        print("Todavía no hay suficiente texto en las reseñas para analizar.")
        return

    print("\nTop palabras en lo que te gustó:")
    for w, c in liked_words.most_common(10):
        print(f"  {w:20s} {c}")
    print("\nTop palabras en lo que NO te gustó:")
    for w, c in disliked_words.most_common(10):
        print(f"  {w:20s} {c}")


if __name__ == "__main__":
    compare_models()
    learning_curve_report()
    plot_history()
    review_insights()
