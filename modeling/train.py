"""
Fase Modeling - entrenar y comparar modelos con las features de contenido (TMDB).

Corre validación cruzada para dos formulaciones:
    - Regresión: predecir Your Rating (1-10)
    - Binario:   predecir Your Rating >= 7  ("me gustó de verdad")

Uso:
    ./venv/bin/python modeling/train.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import KFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_preparation.build_features import build, feature_groups


class OverviewEmbedder(BaseEstimator, TransformerMixin):
    """TF-IDF de la sinopsis + TruncatedSVD, con n_components adaptativo.

    Con pocos títulos el vocabulario puede ser menor que n_components y el SVD
    falla; acá se recorta a lo que haya disponible.
    """

    def __init__(self, n_components: int = 25, min_df: int = 3):
        self.n_components = n_components
        self.min_df = min_df

    @staticmethod
    def _flat(X):
        return np.asarray(X).ravel()

    def fit(self, X, y=None):
        self.tfidf_ = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), min_df=self.min_df, max_features=800
        )
        Z = self.tfidf_.fit_transform(self._flat(X))
        k = max(2, min(self.n_components, Z.shape[1] - 1))
        self.svd_ = TruncatedSVD(n_components=k, random_state=42)
        self.svd_.fit(Z)
        return self

    def transform(self, X):
        return self.svd_.transform(self.tfidf_.transform(self._flat(X)))


def make_preprocessor(groups: dict, target_type: str) -> ColumnTransformer:
    overview_vec = OverviewEmbedder(n_components=25, min_df=3)
    keyword_vec = CountVectorizer(min_df=4, binary=True)
    # CV sembrado: sin esto, TargetEncoder (sklearn >=1.9) mezcla los folds sin
    # semilla y las predicciones cambian entre corridas.
    te_cv = KFold(n_splits=5, shuffle=True, random_state=42)

    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), groups["numeric"]),
            ("oh", OneHotEncoder(handle_unknown="ignore"), groups["onehot"]),
            ("dir", TargetEncoder(target_type=target_type, cv=te_cv), groups["target_enc"]),
            ("ovw", overview_vec, groups["overview"]),
            ("kw", keyword_vec, groups["keywords"]),
            ("gen", "passthrough", groups["genre"]),
        ]
    )


def regression(X, y, groups) -> pd.DataFrame:
    """Compara predecir la nota directa vs predecir el desvío respecto de IMDb.

    El desvío (Your Rating - IMDb Rating) resultó más aprendible: reconstruimos
    la nota como IMDb Rating + desvío_predicho.
    """
    pre = make_preprocessor(groups, target_type="continuous")
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    imdb = X["IMDb Rating"].to_numpy()
    resid = y.to_numpy() - imdb

    rows = []

    def record(name, pred):
        err = np.abs(pred - y)
        rows.append({"modelo": name, "MAE": err.mean(),
                     "RMSE": np.sqrt(((pred - y) ** 2).mean()), "±1": (err <= 1).mean()})

    record("Baseline: media de tu nota", np.full(len(y), y.mean()))
    record("Regla fija: IMDb + media(desvío)", imdb + resid.mean())

    direct = {"Ridge (nota directa)": Ridge(alpha=3.0),
              "RandomForest (nota directa)": RandomForestRegressor(n_estimators=400, random_state=42)}
    for name, est in direct.items():
        record(name, cross_val_predict(Pipeline([("pre", pre), ("m", est)]), X, y, cv=cv))

    resid_models = {"Ridge (desvío)": Ridge(alpha=3.0),
                    "RandomForest (desvío)": RandomForestRegressor(n_estimators=400, random_state=42)}
    for name, est in resid_models.items():
        pred_resid = cross_val_predict(Pipeline([("pre", pre), ("m", est)]), X, resid, cv=cv)
        record(name, imdb + pred_resid)

    return pd.DataFrame(rows).set_index("modelo").round(3)


def binary(X, y_rating, groups, threshold=7) -> pd.DataFrame:
    pre = make_preprocessor(groups, target_type="binary")
    y = (y_rating >= threshold).astype(int)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    models = {
        "Baseline": DummyClassifier(strategy="most_frequent"),
        "LogReg": LogisticRegression(C=0.3, max_iter=2000, class_weight="balanced"),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
    }
    rows = []
    for name, est in models.items():
        pipe = Pipeline([("pre", pre), ("m", est)])
        pred = cross_val_predict(pipe, X, y, cv=cv)
        proba = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
        rows.append({"modelo": name, "accuracy": (pred == y).mean(),
                     "balanced_acc": balanced_accuracy_score(y, pred),
                     "roc_auc": roc_auc_score(y, proba)})
    return pd.DataFrame(rows).set_index("modelo").round(3)


def main() -> None:
    X, y = build()
    groups = feature_groups(X)
    print(f"Filas: {len(X)}  |  Features crudas: {X.shape[1]} "
          f"(se expanden con TF-IDF/keywords dentro del pipeline)\n")

    print("--- REGRESIÓN (Your Rating 1-10) ---")
    print(regression(X, y, groups).to_string())

    yb = (y >= 7).astype(int)
    print(f"\n--- BINARIO (Your Rating >= 7) --- positivos: {yb.sum()}/{len(yb)} "
          f"({yb.mean():.1%}), baseline {max(yb.mean(), 1 - yb.mean()):.1%}")
    print(binary(X, y, groups, threshold=7).to_string())


if __name__ == "__main__":
    main()
