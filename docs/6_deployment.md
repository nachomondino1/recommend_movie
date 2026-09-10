# 6. Deployment

## Arquitectura
`modeling/pipeline.py` define **un único** pipeline (preprocesado + modelo), que
comparten las tres etapas:

| Script | Rol |
|---|---|
| `modeling/fit_final.py` | Entrena los 2 modelos finales con **todos** los ratings y los guarda en `models/` (`regressor.joblib`, `classifier.joblib`, `meta.json`). |
| `deployment/predict_watchlist.py` | **Carga** los modelos de `models/`. Si faltan, los entrena. Si `ratings.csv` es más nuevo que el modelo guardado, re-entrena y avisa. Puntúa la watchlist → `outputs/watchlist_scored.csv`. |
| `deployment/build_dashboard.py` | Convierte ese CSV en `outputs/watchlist_dashboard.html`: archivo autocontenido (sin servidor) con tabla buscable/ordenable (título, director, género), nota predicha coloreada y gráfico de distribución. |

Modelos:
- **Regresión** `RandomForestRegressor` sobre el desvío vs IMDb → `pred_rating = IMDb + desvío`.
- **Binario** `GradientBoostingClassifier` sobre `Your Rating ≥ 7` → `p_like`.

`models/` está en `.gitignore` (se regenera). `meta.json` guarda fecha de
entrenamiento, n, mtime de `ratings.csv` y scores de CV.

## Cómo usarlo
```bash
./venv/bin/python run_pipeline.py         # todo; re-entrena si hace falta
# o, si sólo cambió la watchlist y el modelo está al día:
./venv/bin/python run_pipeline.py --skip-tmdb
```
Después abrir `outputs/watchlist_dashboard.html` (doble clic) o el CSV.

## Publicar en GitHub Pages (acceso desde el teléfono)
`build_dashboard.py` escribe también `docs/index.html` (+ `docs/.nojekyll`).

Alta (una sola vez): repo en GitHub → **Settings → Pages** → *Source: Deploy from
a branch* → **Branch: `main` / carpeta `/docs`** → Save. En ~1 min queda en
`https://nachomondino1.github.io/recommend_movie/`.

Actualizar: `run_pipeline.py` && `git add docs/ && git commit && git push`.
Pages redepliega solo.

Nota: el repo es público, así que el dashboard (y `data/raw/*.csv`) son visibles.
El `.env` con el token TMDB está en `.gitignore` y no se publica.

## Cómo interpretar
- `pred_rating`: nota estimada 1–10. Error típico ±1.3 → un 7.4 vs 7.0 es ruido.
- `p_like`: probabilidad estimada de que le pongas ≥ 7. Para ordenar, no como sí/no.
- Confiar en el **orden general** (tercio de arriba vs tercio de abajo).

## Pendiente para una v2
- **Predecir un título suelto por nombre**: `/search` de TMDB en vivo, refactor de
  `build_features` para 1 título, cargar `models/` y devolver la predicción.
  Requiere un modelo con más señal (hoy AUC 0.63) para que valga la pena.
- Un único score coherente (ensemble de los dos modelos; hoy `pred_rating` y
  `p_like` pueden no concordar).
- Re-entrenar automáticamente al actualizar `ratings.csv` (hoy lo detecta
  `predict_watchlist.py` por mtime y avisa/re-entrena).
