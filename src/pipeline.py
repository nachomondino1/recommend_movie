"""
Definición del pipeline final (preprocesado + estimadores).

Va en su propio módulo (no en model.py) para que joblib pueda picklear/unpicklear
`OverviewEmbedder` sin importar cómo se ejecute el entrenamiento (`python -m
src.model` lo corre como __main__, y picklear desde __main__ rompe la carga).
"""

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import GradientBoostingClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, TargetEncoder

LIKE_THRESHOLD = 7


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
