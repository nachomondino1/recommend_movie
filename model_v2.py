"""
Paso 3B: exprimir los metadatos que ya tenemos.

Agrega sobre model.py:
    - Directors  -> target encoding (media de tu nota por director, cross-fit)
    - n_genres   -> cantidad de géneros del título
    - years_since_release -> años entre estreno y fecha en que lo puntuaste
    - is_franchise -> heurística de secuela sobre el título
    - runtime_missing -> flag de duración ausente

Uso:
    ./venv/bin/python model_v2.py          # regresión + binario (umbral 7)

Compara contra los baselines y contra los números del Paso 2 / 3A.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import (
    KFold,
    StratifiedKFold,
    cross_val_predict,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder

DATA = Path("data/ratings.csv")

NUMERIC = [
    "IMDb Rating",
    "Runtime (mins)",
    "Year",
    "log_votes",
    "n_genres",
    "years_since_release",
    "is_franchise",
    "runtime_missing",
]
ONEHOT = ["Title Type"]
TARGET_ENC = ["Directors"]

_FRANCHISE_RE = re.compile(
    r"\b(?:\d+|II|III|IV|V|VI|VII|VIII|IX|X|part|chapter|vol|volume)\b",
    re.IGNORECASE,
)


def build_features_v2(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["log_votes"] = np.log10(df["Num Votes"].clip(lower=1))

    df["runtime_missing"] = df["Runtime (mins)"].isna().astype(int)
    df["Runtime (mins)"] = df["Runtime (mins)"].fillna(df["Runtime (mins)"].median())

    df["n_genres"] = df["Genres"].str.split(", ").str.len()

    rated_year = pd.to_datetime(df["Date Rated"], errors="coerce").dt.year
    df["years_since_release"] = (rated_year - df["Year"]).clip(lower=0)

    df["is_franchise"] = (
        df["Title"].str.contains(_FRANCHISE_RE).fillna(False).astype(int)
    )

    df["Directors"] = df["Directors"].fillna("Unknown")

    genres = df["Genres"].str.get_dummies(sep=", ")
    genres.columns = [f"genre_{c}" for c in genres.columns]

    return pd.concat([df[NUMERIC + ONEHOT + TARGET_ENC], genres], axis=1)


def make_preprocessor(genre_cols: list[str], target_type: str) -> ColumnTransformer:
    # target_type le dice al TargetEncoder cómo tratar y:
    #   "continuous" para la regresión (nota 1-10)
    #   "binary" para la clasificación (0/1)
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC),
            ("oh", OneHotEncoder(handle_unknown="ignore"), ONEHOT),
            ("dir", TargetEncoder(target_type=target_type, cv=5), TARGET_ENC),
            ("gen", "passthrough", genre_cols),
        ]
    )


def run_regression(X, y, genre_cols):
    pre = make_preprocessor(genre_cols, target_type="continuous")
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    models = {
        "Baseline (media)": DummyRegressor(strategy="mean"),
        "Ridge": Ridge(alpha=1.0),
        "Random Forest": RandomForestRegressor(n_estimators=300, random_state=42),
    }
    rows = []
    for name, est in models.items():
        pred = cross_val_predict(Pipeline([("pre", pre), ("m", est)]), X, y, cv=cv)
        err = np.abs(pred - y)
        rows.append(
            {
                "modelo": name,
                "MAE": err.mean(),
                "RMSE": np.sqrt(((pred - y) ** 2).mean()),
                "±1": (err <= 1).mean(),
            }
        )
    print("\n--- REGRESIÓN (predecir la nota exacta) ---")
    print(pd.DataFrame(rows).set_index("modelo").round(3).to_string())


def run_binary(X, y_rating, genre_cols, threshold=7):
    pre = make_preprocessor(genre_cols, target_type="binary")
    y = (y_rating >= threshold).astype(int)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    pos = y.mean()
    print(f"\n--- BINARIO (nota >= {threshold}) ---")
    print(f"Positivos: {y.sum()} ({pos:.1%})  |  baseline: {max(pos, 1 - pos):.1%}")
    models = {
        "Baseline": DummyClassifier(strategy="most_frequent"),
        "LogReg": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, random_state=42, class_weight="balanced"
        ),
    }
    rows = []
    for name, est in models.items():
        pipe = Pipeline([("pre", pre), ("m", est)])
        pred = cross_val_predict(pipe, X, y, cv=cv)
        proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
        rows.append(
            {
                "modelo": name,
                "accuracy": (pred == y).mean(),
                "balanced_acc": balanced_accuracy_score(y, pred),
                "roc_auc": roc_auc_score(y, proba),
            }
        )
    print(pd.DataFrame(rows).set_index("modelo").round(3).to_string())


def main() -> None:
    df = pd.read_csv(DATA)
    X = build_features_v2(df)
    y = df["Your Rating"]
    genre_cols = [c for c in X.columns if c.startswith("genre_")]

    print(f"Filas: {len(X)}  |  Features: {X.shape[1]}")
    run_regression(X, y, genre_cols)
    run_binary(X, y, genre_cols, threshold=7)


if __name__ == "__main__":
    main()
