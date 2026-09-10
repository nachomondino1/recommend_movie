"""
CRISP-DM: Modeling + Deployment (scoring).

Pipeline final (ver docs/4_modeling.md):
    - Regresión : RandomForest sobre el DESVÍO vs IMDb  -> pred = IMDb + desvío
    - Binario   : GradientBoosting sobre  Your Rating >= 7

    python -m src.model           # entrena, guarda en models/ y puntúa la watchlist
    python -m src.model --eval    # + comparación de modelos (CV) y curva de aprendizaje
"""

import argparse
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (balanced_accuracy_score, mean_absolute_error,
                             roc_auc_score)
from sklearn.model_selection import (KFold, StratifiedKFold, cross_val_predict,
                                     learning_curve)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder

from src.config import MODELS, OUTPUTS, RATINGS_CSV, SCORED_CSV, WATCHLIST_CSV
from src.features import build, feature_groups

LIKE_THRESHOLD = 7
REG_PATH = MODELS / "regressor.joblib"
CLF_PATH = MODELS / "classifier.joblib"


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
class OverviewEmbedder(BaseEstimator, TransformerMixin):
    """TF-IDF de la sinopsis + TruncatedSVD, con n_components adaptativo.

    Con pocos títulos el vocabulario puede ser menor que n_components y el SVD
    falla; acá se recorta a lo disponible.
    """

    def __init__(self, n_components: int = 25, min_df: int = 3):
        self.n_components = n_components
        self.min_df = min_df

    @staticmethod
    def _flat(X):
        return np.asarray(X).ravel()

    def fit(self, X, y=None):
        self.tfidf_ = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                      min_df=self.min_df, max_features=800)
        Z = self.tfidf_.fit_transform(self._flat(X))
        k = max(2, min(self.n_components, Z.shape[1] - 1))
        self.svd_ = TruncatedSVD(n_components=k, random_state=42)
        self.svd_.fit(Z)
        return self

    def transform(self, X):
        return self.svd_.transform(self.tfidf_.transform(self._flat(X)))


def make_preprocessor(groups: dict, target_type: str) -> ColumnTransformer:
    # CV sembrado: sin esto, TargetEncoder (sklearn >=1.9) mezcla los folds sin
    # semilla y las predicciones cambian entre corridas.
    te_cv = KFold(n_splits=5, shuffle=True, random_state=42)
    return ColumnTransformer([
        ("num", StandardScaler(), groups["numeric"]),
        ("oh", OneHotEncoder(handle_unknown="ignore"), groups["onehot"]),
        ("dir", TargetEncoder(target_type=target_type, cv=te_cv), groups["target_enc"]),
        ("ovw", OverviewEmbedder(n_components=25, min_df=3), groups["overview"]),
        ("kw", CountVectorizer(min_df=4, binary=True), groups["keywords"]),
        ("gen", "passthrough", groups["genre"]),
    ])


def build_regressor(groups: dict) -> Pipeline:
    """OJO: el target es el DESVÍO (Your Rating - IMDb). Reconstruir con
    pred_nota = IMDb Rating + pipe.predict(X)."""
    return Pipeline([("pre", make_preprocessor(groups, "continuous")),
                     ("m", RandomForestRegressor(n_estimators=400, random_state=42))])


def build_classifier(groups: dict) -> Pipeline:
    return Pipeline([("pre", make_preprocessor(groups, "binary")),
                     ("m", GradientBoostingClassifier(random_state=42))])


# --------------------------------------------------------------------------- #
# Entrenar y guardar / cargar
# --------------------------------------------------------------------------- #
def fit_and_save() -> None:
    X, y = build()
    groups = feature_groups(X)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb
    like = (y >= LIKE_THRESHOLD).astype(int)

    reg, clf = build_regressor(groups), build_classifier(groups)

    cv_mae = mean_absolute_error(
        y, imdb + cross_val_predict(reg, X, resid, cv=KFold(5, shuffle=True, random_state=42)))
    cv_auc = roc_auc_score(
        like, cross_val_predict(clf, X, like, method="predict_proba",
                                cv=StratifiedKFold(5, shuffle=True, random_state=42))[:, 1])

    reg.fit(X, resid)
    clf.fit(X, like)
    joblib.dump(reg, REG_PATH)
    joblib.dump(clf, CLF_PATH)

    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_train": int(len(X)),
        "ratings_csv_mtime": RATINGS_CSV.stat().st_mtime,
        "like_threshold": LIKE_THRESHOLD,
        "cv_mae_rating": round(float(cv_mae), 3),
        "cv_roc_auc_like": round(float(cv_auc), 3),
    }
    (MODELS / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Modelos guardados en {MODELS}/  "
          f"(n={meta['n_train']}, CV MAE={meta['cv_mae_rating']}, CV AUC={meta['cv_roc_auc_like']})")


def load_models():
    if not REG_PATH.exists() or not CLF_PATH.exists():
        print(">> No hay modelo guardado; entreno.")
        fit_and_save()
    elif RATINGS_CSV.stat().st_mtime > REG_PATH.stat().st_mtime:
        print("!! ratings.csv es más nuevo que el modelo guardado; re-entreno.")
        fit_and_save()
    return joblib.load(REG_PATH), joblib.load(CLF_PATH)


# --------------------------------------------------------------------------- #
# Scoring de la watchlist
# --------------------------------------------------------------------------- #
def score_watchlist() -> pd.DataFrame:
    reg, clf = load_models()
    X_tr, _ = build()
    X_wl, _ = build(WATCHLIST_CSV)
    X_wl = X_wl.reindex(columns=X_tr.columns, fill_value=0)

    wl = pd.read_csv(WATCHLIST_CSV)
    wl["pred_rating"] = (X_wl["IMDb Rating"].to_numpy() + reg.predict(X_wl)).clip(1, 10)
    wl["p_like"] = clf.predict_proba(X_wl)[:, 1]
    wl["Directors"] = wl["Directors"].fillna("")

    cols = ["Title", "Year", "Title Type", "IMDb Rating", "Directors", "Genres",
            "pred_rating", "p_like"]
    out = (wl[cols].sort_values("pred_rating", ascending=False)
           .round({"pred_rating": 1, "p_like": 2}).reset_index(drop=True))
    out.to_csv(SCORED_CSV, index=False)
    print(f"\nGuardado: {SCORED_CSV}  ({len(out)} títulos)")
    print("\nTOP 10:")
    print(out.head(10).to_string())
    return out


# --------------------------------------------------------------------------- #
# Diagnósticos (--eval)
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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval", action="store_true",
                    help="además: comparación de modelos (CV) y curva de aprendizaje")
    args = ap.parse_args()

    fit_and_save()
    score_watchlist()
    if args.eval:
        compare_models()
        learning_curve_report()
