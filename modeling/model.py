"""
Primer modelo: predecir "Your Rating" a partir de metadatos de IMDb.

Uso:
    ./venv/bin/python model.py

Compara varios modelos con validación cruzada 5-fold sobre data/ratings.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "ratings.csv"

NUMERIC = ["IMDb Rating", "Runtime (mins)", "Year", "log_votes"]
CATEGORICAL = ["Title Type"]


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Devuelve (X, y) ya listos para el pipeline."""
    df = df.copy()

    # log de votos: la cantidad de votos tiene una cola muy larga
    df["log_votes"] = np.log10(df["Num Votes"].clip(lower=1))

    # duración: 3 faltantes -> imputamos con la mediana
    df["Runtime (mins)"] = df["Runtime (mins)"].fillna(df["Runtime (mins)"].median())

    # géneros -> columnas indicadoras (multi-hot)
    genres = df["Genres"].str.get_dummies(sep=", ")
    genres.columns = [f"genre_{c}" for c in genres.columns]

    X = pd.concat([df[NUMERIC + CATEGORICAL], genres], axis=1)
    y = df["Your Rating"]
    return X, y


def make_preprocessor(genre_cols: list[str]) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
            ("gen", "passthrough", genre_cols),
        ]
    )


def evaluate(name: str, pipe: Pipeline, X: pd.DataFrame, y: pd.Series) -> dict:
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    pred = cross_val_predict(pipe, X, y, cv=cv)
    err = np.abs(pred - y)
    return {
        "modelo": name,
        "MAE": err.mean(),
        "RMSE": np.sqrt(((pred - y) ** 2).mean()),
        "±1": (err <= 1).mean(),
        "±2": (err <= 2).mean(),
    }


def main() -> None:
    df = pd.read_csv(DATA)
    X, y = build_features(df)
    genre_cols = [c for c in X.columns if c.startswith("genre_")]
    pre = make_preprocessor(genre_cols)

    models = {
        "Baseline (media)": DummyRegressor(strategy="mean"),
        "Ridge": Ridge(alpha=1.0),
        "Random Forest": RandomForestRegressor(n_estimators=300, random_state=42),
        "KNN (k=7)": KNeighborsRegressor(n_neighbors=7),
    }

    rows = []
    for name, est in models.items():
        pipe = Pipeline([("pre", pre), ("model", est)])
        rows.append(evaluate(name, pipe, X, y))

    res = pd.DataFrame(rows).set_index("modelo").round(3)
    print(f"\nFilas: {len(X)}  |  Features: {X.shape[1]}  |  CV: 5-fold\n")
    print(res.to_string())
    print("\nMAE = error absoluto medio (más bajo mejor)")
    print("±1  = fracción de predicciones que caen a 1 punto o menos de tu nota real")


if __name__ == "__main__":
    main()
