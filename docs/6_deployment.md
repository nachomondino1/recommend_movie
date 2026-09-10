# 6. Deployment

## Arquitectura
`src/model.py` define **un único** pipeline (preprocesado + modelo) y todo lo que
lo rodea:

| Función (`src/model.py`) | Rol |
|---|---|
| `build_regressor` / `build_classifier` | Definición del pipeline final. |
| `fit_and_save()` | Entrena los 2 modelos con **todos** los ratings y los guarda en `models/` (`regressor.joblib`, `classifier.joblib`, `meta.json`). |
| `load_models()` | Carga de `models/`. Si faltan, entrena. Si `ratings.csv` es más nuevo que el modelo guardado, re-entrena y avisa. |
| `score_watchlist()` | Puntúa la watchlist → `outputs/watchlist_scored.csv`. |
| `compare_models()`, `learning_curve_report()` | Diagnósticos (`make eval`). |

`src/dashboard.py` convierte el CSV puntuado en un HTML autocontenido (sin
servidor) con tabla buscable/ordenable (título, director, género), nota predicha
coloreada y gráfico de distribución. Lo escribe en `outputs/watchlist_dashboard.html`
y en `docs/index.html` (lo que publica Pages). Los títulos de la watchlist que ya
figuran puntuados en `ratings.csv` se omiten.

`src/predict.py` (`make predict TITLE="X"`) resuelve un título por nombre con
`/search/multi` de TMDB, arma la fila con `features.build_row()` y aplica los
modelos guardados. Sirve para evaluar algo que no está en la watchlist.

`metrics_history.csv` (versionado) acumula una fila por tamaño de dataset con la
fecha y los scores de CV. `make eval` grafica esa **trayectoria real** en
`outputs/metrics_history.png` (distinta de la curva de aprendizaje, que es simulada).

Modelos:
- **Regresión** `RandomForestRegressor` sobre el desvío vs IMDb → `pred_rating = IMDb + desvío`.
- **Binario** `GradientBoostingClassifier` sobre `Your Rating ≥ 7` → `p_like`.

`models/` está en `.gitignore` (se regenera). `meta.json` guarda fecha de
entrenamiento, n, mtime de `ratings.csv` y scores de CV.

## Cómo usarlo
```bash
make update      # src.data -> src.model -> src.dashboard
make publish     # git add docs/ && commit && push -> Pages redepliega
```
Para mirar local: abrir `outputs/watchlist_dashboard.html` con doble clic.

## GitHub Pages (acceso desde el teléfono)
Alta (una sola vez): repo en GitHub → **Settings → Pages** → *Source: Deploy from
a branch* → **Branch `main` / carpeta `/docs`** → Save. En ~1 min queda en
`https://nachomondino1.github.io/recommend_movie/`.

Nota: el repo es público, así que el dashboard (y `data/*.csv`) son visibles.
El `.env` con el token TMDB está en `.gitignore` y no se publica.

## Cómo interpretar
- `pred_rating`: nota estimada 1–10. Error típico ±1.3 → un 7.4 vs 7.0 es ruido.
- `p_like`: probabilidad estimada de que le pongas ≥ 7. Para ordenar, no como sí/no.
- Confiar en el **orden general** (tercio de arriba vs tercio de abajo).

## Pendiente para una v2
- Un único score coherente (ensemble de los dos modelos; hoy `pred_rating` y
  `p_like` pueden no concordar).
- Embeddings de sinopsis (sentence-transformers) en lugar de TF-IDF, cuando haya
  más ratings.
- `make predict` toma sólo el primer resultado de TMDB; con títulos ambiguos
  convendría mostrar candidatos y elegir.
