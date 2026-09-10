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
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (balanced_accuracy_score, mean_absolute_error,
                             roc_auc_score)
from sklearn.model_selection import (KFold, StratifiedKFold, cross_val_predict,
                                     learning_curve)
from sklearn.pipeline import Pipeline

from src.config import (METRICS_CSV, MODELS, OUTPUTS, RATINGS_CSV, SCORED_CSV,
                        WATCHLIST_CSV)
from src.features import build, feature_groups
from src.pipeline import (LIKE_THRESHOLD, OverviewEmbedder, build_classifier,  # noqa: F401
                          build_regressor, make_preprocessor)

REG_PATH = MODELS / "regressor.joblib"
CLF_PATH = MODELS / "classifier.joblib"


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
        "feature_columns": list(X.columns),
    }
    (MODELS / "meta.json").write_text(json.dumps(meta, indent=2))
    _append_history(meta)
    print(f"Modelos guardados en {MODELS}/  "
          f"(n={meta['n_train']}, CV MAE={meta['cv_mae_rating']}, CV AUC={meta['cv_roc_auc_like']})")


def _append_history(meta: dict) -> None:
    """Registra la trayectoria real de scores: una fila por tamaño de dataset."""
    row = {"date": meta["trained_at"][:10], "n_train": meta["n_train"],
           "cv_mae_rating": meta["cv_mae_rating"], "cv_roc_auc_like": meta["cv_roc_auc_like"]}
    hist = pd.read_csv(METRICS_CSV) if METRICS_CSV.exists() else pd.DataFrame()
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    hist = hist.drop_duplicates("n_train", keep="last").sort_values("n_train")
    hist.to_csv(METRICS_CSV, index=False)


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

    wl = pd.read_csv(WATCHLIST_CSV)
    rated = set(pd.read_csv(RATINGS_CSV)["Const"].dropna())
    keep = ~wl["Const"].isin(rated)          # sacar los que ya viste y puntuaste
    n_drop = int((~keep).sum())
    wl = wl[keep].reset_index(drop=True)

    X_wl, _ = build(WATCHLIST_CSV)
    X_wl = X_wl[keep.to_numpy()].reset_index(drop=True).reindex(columns=X_tr.columns, fill_value=0)

    wl["pred_rating"] = (X_wl["IMDb Rating"].to_numpy() + reg.predict(X_wl)).clip(1, 10)
    wl["p_like"] = clf.predict_proba(X_wl)[:, 1]
    wl["Directors"] = wl["Directors"].fillna("")
    if n_drop:
        print(f"({n_drop} títulos de la watchlist ya estaban puntuados; se omiten)")

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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval", action="store_true",
                    help="además: comparación de modelos (CV), curva de aprendizaje y trayectoria")
    args = ap.parse_args()

    fit_and_save()
    score_watchlist()
    if args.eval:
        compare_models()
        learning_curve_report()
        plot_history()
