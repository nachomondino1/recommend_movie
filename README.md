# recommend_movie

Recomendador personal de películas y series: entrena con las notas que puse en
IMDb y predice qué nota le pondría a un título que todavía no vi, para priorizar
la watchlist.

**Dashboard en vivo:** https://nachomondino1.github.io/recommend_movie/

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
| `make publish` | `git add docs/ && commit && push` → Pages se redespliega. |
| `make eval` | Diagnósticos: comparación de modelos (CV) + curva de aprendizaje. |
| `make explore` | Análisis exploratorio (gráficos en `outputs/`). |

No hace falta acordarse de qué correr cuando cambia `ratings.csv` vs `watchlist.csv`:
en ambos casos es `make update`.

## Estructura

```
data/
  ratings.csv, watchlist.csv     exportaciones de IMDb (versionadas)
  cache/                          TMDB json + tabla (regenerable, git-ignored)
src/
  config.py      paths y carga de .env
  data.py        cargar CSVs + cliente TMDB + enriquecimiento
  features.py    matriz de features (IMDb + TMDB)
  model.py       pipeline, entrenar/guardar, cargar, puntuar watchlist, diagnósticos
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
