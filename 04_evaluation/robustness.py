"""
CRISP-DM: Evaluación - ¿algún modelo le gana de verdad a la nota de IMDb?

`evaluate.py` compara modelos con UNA validación cruzada de 5 folds. Con ~127 notas eso es
ruidoso: una diferencia de 0,03 puntos de MAE puede ser suerte del reparto. Este script le da
una prueba más dura a la conclusión "no encontré nada que le gane a IMDb":

  1. Validación cruzada REPETIDA (5 folds x 10 repeticiones): cada predicción es fuera de muestra.
  2. Varias familias de modelos, todas contra la misma base justa: la nota de IMDb CALIBRADA
     a tu escala (nota = a + b·IMDb, ajustada solo con el train de cada fold).
  3. Intervalos de confianza por bootstrap PAREADO sobre los títulos (la diferencia de cada
     modelo contra IMDb, con su IC 95 %), no solo un promedio.
  4. Control de permutación: ¿el modelo detecta señal real o solo ruido?
  5. Poder estadístico: qué mejora mínima podría detectar un dataset de este tamaño.
  6. Curva de aprendizaje repetida, con bandas de error, del modelo contra la base IMDb.

    python 04_evaluation/robustness.py
"""

import sys
import warnings
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import OUTPUTS
from features import build, feature_groups
from pipeline import LIKE_THRESHOLD, make_preprocessor

warnings.filterwarnings("ignore")
SEED = 7
REPEATS = 10
N_BOOT = 5000


# --------------------------------------------------------------------------- #
# Candidatos: cada uno es fit_predict(Xtr, ytr, Xte) -> nota predicha
# --------------------------------------------------------------------------- #
def _imdb(X) -> np.ndarray:
    return X["IMDb Rating"].to_numpy(dtype=float)


def mean_model(Xtr, ytr, Xte):
    return np.full(len(Xte), ytr.mean())


def imdb_raw(Xtr, ytr, Xte):
    return _imdb(Xte)


def imdb_calibrated(Xtr, ytr, Xte):
    """La base JUSTA: IMDb reescalada a tu forma de puntuar (a + b·IMDb)."""
    b, a = np.polyfit(_imdb(Xtr), ytr, 1)
    return a + b * _imdb(Xte)


def _deviation_model(make_pre, estimator):
    """Predice el desvío (tu nota - IMDb calibrada) y lo suma a la base."""
    def fit_predict(Xtr, ytr, Xte):
        base_tr, base_te = imdb_calibrated(Xtr, ytr, Xtr), imdb_calibrated(Xtr, ytr, Xte)
        pipe = Pipeline([("pre", make_pre(Xtr)), ("m", clone(estimator))])
        pipe.fit(Xtr, ytr - base_tr)
        return base_te + pipe.predict(Xte)
    return fit_predict


def _simple_pre(Xtr):
    genres = [c for c in Xtr.columns if c.startswith("genre_")]
    return ColumnTransformer([
        ("num", StandardScaler(), ["Year", "Runtime (mins)", "log_votes", "IMDb Rating"]),
        ("oh", OneHotEncoder(handle_unknown="ignore"), ["Title Type"]),
        ("gen", "passthrough", genres),
    ])


def _full_pre_factory(groups):
    return lambda Xtr: make_preprocessor(groups, "continuous")


def genre_shrinkage(Xtr, ytr, Xte, k=10.0):
    """Desvío medio por género con encogimiento hacia el desvío global (empirical-Bayes)."""
    base_tr, base_te = imdb_calibrated(Xtr, ytr, Xtr), imdb_calibrated(Xtr, ytr, Xte)
    dev = ytr - base_tr
    mu = dev.mean()
    genres = [c for c in Xtr.columns if c.startswith("genre_")]
    G = Xtr[genres].to_numpy(dtype=float)
    shrunk = np.array([mu + (dev[G[:, j] == 1].sum() - mu * (G[:, j] == 1).sum()) / ((G[:, j] == 1).sum() + k)
                       for j in range(len(genres))])
    Gt = Xte[genres].to_numpy(dtype=float)
    adj = np.where(Gt.sum(1) > 0, (Gt @ (shrunk - mu)) / np.maximum(Gt.sum(1), 1), 0.0)
    return base_te + mu + adj


def build_candidates(groups):
    full = _full_pre_factory(groups)
    cands = {
        "Media de tu nota": mean_model,
        "IMDb tal cual": imdb_raw,
        "IMDb calibrada (BASE)": imdb_calibrated,
        "Géneros con encogimiento": genre_shrinkage,
        "Ridge simple (géneros, año, duración, votos)": _deviation_model(_simple_pre, Ridge(alpha=30)),
        "Ridge con todas las variables": _deviation_model(full, Ridge(alpha=30)),
        "RandomForest (todas)": _deviation_model(full, RandomForestRegressor(200, min_samples_leaf=3, random_state=SEED, n_jobs=-1)),
        "GradientBoosting (todas)": _deviation_model(full, GradientBoostingRegressor(n_estimators=80, max_depth=2, learning_rate=0.05, subsample=0.7, random_state=SEED)),
    }
    ens_a, ens_b = cands["Ridge simple (géneros, año, duración, votos)"], cands["RandomForest (todas)"]
    cands["Promedio Ridge + RandomForest"] = lambda a, b, c: (ens_a(a, b, c) + ens_b(a, b, c)) / 2
    return cands


# --------------------------------------------------------------------------- #
# Validación y métricas
# --------------------------------------------------------------------------- #
def oof_predictions(fn, X, y):
    """Predicción fuera de muestra de cada título, promediada sobre REPEATS repartos distintos."""
    preds = np.zeros((REPEATS, len(y)))
    for r in range(REPEATS):
        for tr, te in KFold(5, shuffle=True, random_state=SEED + r).split(X):
            preds[r, te] = fn(X.iloc[tr], y[tr], X.iloc[te])
    return preds


def metrics(pred, y, like):
    return {
        "MAE": np.abs(pred - y).mean(),
        "RMSE": np.sqrt(((pred - y) ** 2).mean()),
        "Spearman": spearmanr(pred, y)[0],
        "AUC(>=7)": roc_auc_score(like, pred),
    }


def paired_bootstrap(a_pred, b_pred, y, like, rng):
    """Diferencia (a - b) de MAE y de AUC, remuestreando títulos. a = modelo, b = base."""
    n = len(y)
    d_mae, d_auc = [], []
    ea, eb = np.abs(a_pred - y), np.abs(b_pred - y)
    for _ in range(N_BOOT):
        i = rng.integers(0, n, n)
        d_mae.append(ea[i].mean() - eb[i].mean())
        if 0 < like[i].sum() < n:
            d_auc.append(roc_auc_score(like[i], a_pred[i]) - roc_auc_score(like[i], b_pred[i]))
    d_mae, d_auc = np.array(d_mae), np.array(d_auc)
    return d_mae, d_auc


def ci(a):
    return np.percentile(a, [2.5, 97.5])


# --------------------------------------------------------------------------- #
# Reporte
# --------------------------------------------------------------------------- #
def main():
    rng = np.random.default_rng(SEED)
    X, y_s = build()
    X = X.reset_index(drop=True)
    y = y_s.to_numpy(dtype=float)
    like = (y >= LIKE_THRESHOLD).astype(int)
    groups = feature_groups(X)
    cands = build_candidates(groups)
    n = len(y)
    print(f"n = {n} títulos puntuados · {REPEATS} repeticiones de CV de 5 folds · {N_BOOT} remuestreos bootstrap\n")

    oof = {}
    for name, fn in cands.items():
        oof[name] = oof_predictions(fn, X, y).mean(axis=0)
        print(f"  listo: {name}")

    base_name = "IMDb calibrada (BASE)"
    rows, boots = [], {}
    for name, p in oof.items():
        m = metrics(p, y, like)
        row = {"modelo": name, **m}
        if name != base_name:
            d_mae, d_auc = paired_bootstrap(p, oof[base_name], y, like, rng)
            boots[name] = (d_mae, d_auc)
            lo, hi = ci(d_mae)
            row.update({"ΔMAE vs BASE": d_mae.mean(), "IC95 ΔMAE": f"[{lo:+.3f}, {hi:+.3f}]",
                        "P(mejor que BASE)": (d_mae < 0).mean(),
                        "ΔAUC vs BASE": d_auc.mean(), "IC95 ΔAUC": f"[{ci(d_auc)[0]:+.3f}, {ci(d_auc)[1]:+.3f}]"})
        rows.append(row)
    table = pd.DataFrame(rows).set_index("modelo")
    print("\n=== COMPARACIÓN (menor MAE/RMSE y mayor Spearman/AUC es mejor) ===")
    print(table.round(3).to_string())
    table.round(4).to_csv(OUTPUTS / "robustness_comparison.csv")

    # ---- Poder estadístico ----------------------------------------------------------
    best = min(boots, key=lambda k: boots[k][0].mean())
    se = boots[best][0].std()
    print(f"\n=== PODER ESTADÍSTICO ===\nMejor candidato por MAE: {best}")
    print(f"Error estándar de la diferencia de MAE contra la base: {se:.3f}")
    print(f"Mejora mínima detectable (80 % de poder, 95 % de confianza) ≈ {2.8 * se:.2f} puntos de MAE")

    # ---- Control de permutación -----------------------------------------------------
    print("\n=== CONTROL DE PERMUTACIÓN (Ridge simple) ===")
    fn = cands["Ridge simple (géneros, año, duración, votos)"]
    real = np.abs(oof_predictions(fn, X, y).mean(axis=0) - y).mean() - np.abs(oof[base_name] - y).mean()
    null = []
    for s in range(150):
        # Se mezclan las filas de X respecto de y (se rompe la relación de tus gustos con los
        # géneros, etc.) pero se conserva la nota de IMDb de cada título pegada a TU nota real.
        perm = rng.permutation(n)
        Xp = X.copy()
        keep = ["IMDb Rating"]
        Xp[[c for c in X.columns if c not in keep]] = X[[c for c in X.columns if c not in keep]].iloc[perm].to_numpy()
        pp = np.zeros(n)
        for tr, te in KFold(5, shuffle=True, random_state=s).split(Xp):
            pp[te] = fn(Xp.iloc[tr], y[tr], Xp.iloc[te])
        bp = np.zeros(n)
        for tr, te in KFold(5, shuffle=True, random_state=s).split(Xp):
            bp[te] = imdb_calibrated(Xp.iloc[tr], y[tr], Xp.iloc[te])
        null.append(np.abs(pp - y).mean() - np.abs(bp - y).mean())
    null = np.array(null)
    print(f"ΔMAE real (modelo - base): {real:+.3f}")
    print(f"ΔMAE con las otras variables mezcladas al azar: media {null.mean():+.3f}, "
          f"percentil 5 {np.percentile(null, 5):+.3f}")
    print(f"Proporción de mezclas que igualan o superan al modelo real: {(null <= real).mean():.2f}")

    learning_curve(cands, X, y, rng)
    forest_plot(boots)


def learning_curve(cands, X, y, rng):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = ["IMDb calibrada (BASE)", "Ridge simple (géneros, año, duración, votos)", "RandomForest (todas)"]
    sizes, reps, n_test = [30, 50, 70, 90, 100], 25, 25
    res = {nm: {s: [] for s in sizes} for nm in names}
    for r in range(reps):
        idx = rng.permutation(len(y))
        te, pool = idx[:n_test], idx[n_test:]
        for s in sizes:
            tr = pool[:s]
            for nm in names:
                p = cands[nm](X.iloc[tr], y[tr], X.iloc[te])
                res[nm][s].append(np.abs(p - y[te]).mean())
    print("\n=== CURVA DE APRENDIZAJE (MAE en 25 títulos reservados; 25 repeticiones) ===")
    print("   n  | " + " | ".join(f"{nm[:22]:>22}" for nm in names) + " | Ridge−BASE")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = {names[0]: "tab:gray", names[1]: "tab:blue", names[2]: "tab:red"}
    for nm in names:
        m = np.array([np.mean(res[nm][s]) for s in sizes])
        se = np.array([np.std(res[nm][s]) / np.sqrt(reps) for s in sizes])
        ax.plot(sizes, m, "o-", color=colors[nm], label=nm.split(" (")[0])
        ax.fill_between(sizes, m - se, m + se, color=colors[nm], alpha=.15)
    for s in sizes:
        row = [np.mean(res[nm][s]) for nm in names]
        print(f"  {s:3d} | " + " | ".join(f"{v:22.3f}" for v in row) + f" | {row[1] - row[0]:+.3f}")
    ax.set(xlabel="títulos usados para entrenar", ylabel="error medio (MAE) en títulos no vistos",
           title="¿Mejora el modelo frente a IMDb al sumar datos?")
    ax.legend(); fig.tight_layout()
    fig.savefig(OUTPUTS / "learning_curve_robust.png", dpi=140)
    print(f"Gráfico: {OUTPUTS / 'learning_curve_robust.png'}")


def forest_plot(boots):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(boots)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for i, nm in enumerate(names):
        d = boots[nm][0]
        lo, hi = ci(d)
        ax.plot([lo, hi], [i, i], color="tab:blue", lw=3)
        ax.plot(d.mean(), i, "o", color="white", mec="tab:blue", ms=7)
    ax.axvline(0, color="gray", ls="--")
    ax.set_yticks(range(len(names))); ax.set_yticklabels([n[:34] for n in names])
    ax.set(xlabel="diferencia de MAE contra IMDb calibrada (izquierda = mejor que IMDb)",
           title="Cada modelo contra la nota de IMDb (IC 95 %)")
    fig.tight_layout()
    fig.savefig(OUTPUTS / "model_vs_imdb.png", dpi=140)
    print(f"Gráfico: {OUTPUTS / 'model_vs_imdb.png'}")


if __name__ == "__main__":
    main()
