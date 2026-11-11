# recommend_movie

Recomendador personal de películas y series: entrena con las notas que puse en
IMDb y predice qué nota le pondría a un título que todavía no vi, para priorizar
la watchlist.

**Dashboard en vivo:** https://nachomondino1.github.io/recommend_movie/

## MVP público (ramas `staging` → `prod`)

Versión para que cualquiera la use: subís tu export de IMDb, elegís tus plataformas y te ordena qué ver (tu watchlist y títulos nuevos) según tu gusto. Estructura por fases CRISP-DM, como `boardgame`:

| Fase | Carpeta |
|---|---|
| 1. Entender / recolectar (TMDB + **log de la API**) | [`01_data_understanding/`](01_data_understanding/README.md) |
| 2. Preparar (catálogo del sitio) | [`02_data_preparation/`](02_data_preparation/README.md) |
| 3. Modelado (regla de afinidad, sin modelo entrenado) | [`03_modeling/`](03_modeling/README.md) |
| 4. Evaluación | [`04_evaluation/`](04_evaluation/README.md) |
| 5. Despliegue (ramas, PR a `prod`) | [`05_deployment/`](05_deployment/README.md) |

El sitio está en `docs/mvp/` y no llama a ninguna API. Datos: `./sync_data.sh`. El proyecto personal (modelo entrenado, `make update`) sigue en `src/` y más abajo.

## Uso

Actualizás los datos y regenerás todo con **un comando**:

```bash
# 1. bajar ratings.csv y watchlist.csv de IMDb y ponerlos en data/
#    (https://www.imdb.com/user/p.uwndhvvnyyx5vbgle5q7rfxsfy/ratings/)
make update      # enriquece con TMDB, entrena, puntúa la watchlist, regenera el dashboard
make publish     # sube el dashboard a GitHub Pages
```

| Comando | Qué hace |
|---|---|
| `make setup` | Crear venv e instalar dependencias (una sola vez). Después completar `TMDB_TOKEN` en `.env`. |
| `make update` | `src.data` (TMDB) → `src.model` (entrena + guarda + puntúa) → `src.dashboard` (HTML). |
| `make predict TITLE="X"` | Nota predicha para un título por nombre (aunque no esté en la watchlist). |
| `make review TITLE="X" TEXT="..."` | Guardar/actualizar tu reseña personal (texto libre) de un título. |
| `make publish` | `git add docs/ && commit && push` → Pages se redespliega. |
| `make eval` | Diagnósticos: modelos (CV) + curva de aprendizaje + trayectoria real de scores + reseñas. |
| `make explore` | Análisis exploratorio (gráficos en `outputs/`). |

No hace falta acordarse de qué correr cuando cambia `ratings.csv` vs `watchlist.csv`:
en ambos casos es `make update`.

## Estructura

```
data/
  ratings.csv, watchlist.csv     exportaciones de IMDb (versionadas)
  reviews.csv                     tu reseña personal por título (versionada; make review)
  metrics_history.csv            scores CV por tamaño de dataset (versionado; crece con make update)
  cache/                          TMDB json + tabla (regenerable, git-ignored)
src/
  config.py      paths y carga de .env
  data.py        cargar CSVs + cliente TMDB + enriquecimiento
  features.py    matriz de features (IMDb + TMDB); build() y build_row() (1 título)
  pipeline.py    definición del pipeline (preprocesado + estimadores)
  model.py       entrenar/guardar, cargar, puntuar watchlist, diagnósticos, insight de reseñas
  predict.py     nota predicha para un título por nombre (make predict)
  curate.py      marcar como vista o "no me interesa" (make watched / make skip)
  review.py      guardar tu reseña personal de un título (make review)
  dashboard.py   generar el HTML (outputs/ + docs/index.html)
notebooks/
  exploration.py análisis exploratorio (one-off)
docs/            narrativa CRISP-DM (1..6) + index.html publicado por Pages
models/          modelos entrenados (git-ignored)
outputs/         gráficos y CSVs locales (git-ignored)
```

La metodología sigue CRISP-DM; cada fase está documentada en `docs/` y el código
en `src/` está ordenado en ese mismo flujo.

## Estado actual

- Mejor regresión: RandomForest sobre el desvío vs IMDb, **MAE 1.26** (baseline 1.31).
- Mejor binario (≥7): Gradient Boosting, **ROC AUC 0.63** (baseline 0.50).
- Cuello de botella: cantidad de datos (126 títulos puntuados). La curva de
  aprendizaje no saturó → más ratings es la mejora con mejor retorno. Ver
  [`docs/4_modeling.md`](docs/4_modeling.md).

## Links

- Datos: https://www.imdb.com/user/p.uwndhvvnyyx5vbgle5q7rfxsfy/ratings/
- API TMDB: https://www.themoviedb.org/settings/api (token v4 → `.env`)
- Deploy: https://nachomondino1.github.io/recommend_movie/
