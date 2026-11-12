# ¿Qué hace que una película tenga buena nota?

Proyecto de datos con Machine Learning y una sola fuente, la API de TMDB: con la nota pública de miles de películas y
series (8.493, de las plataformas disponibles en Argentina) se entrena un modelo y se mide qué características pesan más.
La web publica el flujo CRISP-DM completo, las conclusiones y los resultados. No hay servidor: todo sale de un archivo de
resultados (`docs/data/model_results.json`).

**Sitio en vivo:** https://nachomondino1.github.io/recommend_movie/

> **Versión 1 (en el historial y en el código):** el proyecto empezó prediciendo la nota *personal* a partir de las 127 notas de
> IMDb de una persona. Con tan pocos datos ningún modelo le ganó a la nota de IMDb, así que la versión 2 cambia la respuesta
> (la nota pública), la fuente (solo TMDB) y la cantidad de datos. Los módulos de la versión 1 (`build_model.py`,
> `assess_model.py`, `test_design.py`, `features.py`) siguen en el repositorio y ya no alimentan la web.

## Versión 2: cómo correrla

```bash
make drivers     # prepare_titles.py (fase 02) + drivers_model.py (fase 03): data/03_modeling/drivers_results.json
make results     # deja docs/data/model_results.json listo para la web
make serve       # http://localhost:8765
```

Para bajar los datos crudos hace falta `TMDB_TOKEN` en `.env`:
`python3 01_data_understanding/collect_initial_data/tmdb/refresh_tmdb_data.py` (catálogo) y
`python3 01_data_understanding/collect_initial_data/tmdb/fetch_credits.py` (elencos y equipo).

## Comandos

**Correr el sitio en local** (http://localhost:8765):

```bash
make serve                  # o: make serve PORT=9000
# equivalente sin make:
cd docs
python3 -m http.server 8765
```

Necesita un servidor (no abre con doble clic) porque la página carga `data/model_results.json`.

**Actualizar el catálogo de películas y series** (recolecta de TMDB, arma `docs/data/catalog.json` y commitea en `staging`):

```bash
make sync                   # o: ./sync_data.sh   (necesita TMDB_TOKEN en .env)
./sync_data.sh --top 800    # cualquier argumento va a refresh_tmdb_data.py
```

Cada corrida suma una fila a [`01_data_understanding/refresh_log.md`](01_data_understanding/refresh_log.md) (requests a la API, nuevos, errores, duración).

**Cada paso por separado:**

```bash
python3 01_data_understanding/collect_initial_data/tmdb/refresh_tmdb_data.py [--dry-run]   # 1. recolectar de TMDB
python3 01_data_understanding/verify_data_quality.py                                      # 1. verificar calidad
python3 02_data_preparation/build_catalog.py                                              # 2. armar el catálogo del sitio
```

**Publicar** (todo cambio entra por `staging`; `prod` solo recibe pull requests):

```bash
git push origin staging
gh pr create --base prod --head staging --title "..." --body "..."
```

**Proyecto personal** (modelo entrenado sobre tus notas): `make setup` una vez, y después `make update`, `make eval`, `make predict TITLE="X"`. Ver [Proyecto personal](#proyecto-personal-modelo-entrenado) más abajo y `make` para la lista completa.

## Estructura por fases (ramas `staging` → `prod`)

Estructura CRISP-DM, como `boardgame`:

| Fase | Carpeta |
|---|---|
| 1. Entender / recolectar (TMDB + **log de la API**) | [`01_data_understanding/`](01_data_understanding/README.md) |
| 2. Preparar (catálogo del sitio) | [`02_data_preparation/`](02_data_preparation/README.md) |
| 3. Modelado (el MVP no predice nada: ordena por nota) | [`03_modeling/`](03_modeling/README.md) |
| 4. Evaluación | [`04_evaluation/`](04_evaluation/README.md) |
| 5. Despliegue (ramas, PR a `prod`) | [`05_deployment/`](05_deployment/README.md) |

El sitio es `docs/` (lo que publica Pages) y no llama a ninguna API. Datos: `./sync_data.sh`. El proyecto personal (modelo entrenado, `make update`) sigue en estas mismas carpetas (ver "Estructura" más abajo).

## Proyecto personal (modelo entrenado)

Predice qué nota le pondría a un título que todavía no vi, entrenando con las notas que puse en IMDb. Actualizás los datos y regenerás todo con **un comando**:

```bash
# 1. bajar ratings.csv y watchlist.csv de IMDb y ponerlos en data/
#    (https://www.imdb.com/user/p.uwndhvvnyyx5vbgle5q7rfxsfy/ratings/)
make update      # enriquece con TMDB, entrena, puntúa la watchlist, regenera el dashboard
make explore     # análisis exploratorio (el sitio público se actualiza con ./sync_data.sh)
```

| Comando | Qué hace |
|---|---|
| `make setup` | Crear venv e instalar dependencias (una sola vez). Después completar `TMDB_TOKEN` en `.env`. |
| `make update` | `tmdb_data.py` (TMDB, crudo) → `prepare_tmdb.py` (tabla) → `build_model.py` (entrena + guarda + puntúa) → `build_model.py catalog` → `dashboard.py` (HTML). |
| `make predict TITLE="X"` | Nota predicha para un título por nombre (aunque no esté en la watchlist). |
| `make eval` | Diagnósticos: modelos (CV) + curva de aprendizaje + trayectoria real de scores + reseñas (`assess_model.py`). |
| `make robust` | Prueba de robustez (~80 s): ¿algún modelo le gana de verdad a la nota de IMDb? |
| `make results` | Deja los resultados de `make robust` listos para la portada de la web (`docs/data/model_results.json`). |
| `make explore` | Análisis exploratorio (gráficos en `data/01_data_understanding/exploration/`). |

No hace falta acordarse de qué correr cuando cambia `ratings.csv` vs `watchlist.csv`:
en ambos casos es `make update`.

## Estructura de carpetas

```
data/                              todo lo que entra y sale de cada fase, en la carpeta de su fase
  01_data_understanding/
    imdb/                        ratings.csv, watchlist.csv (exportaciones de IMDb) y reviews.csv
    tmdb/                        JSON crudo de TMDB: titles/ (uno por título) y el catálogo del sitio (jsonl + json)
    exploration/                 gráficos del análisis exploratorio (git-ignored)
  03_modeling/                   puntuaciones (*_scored.csv), gráficos de evaluación y las métricas
                                 (metrics_history.csv y robustness_comparison.csv se versionan)
  05_deployment/                 dashboard personal generado (git-ignored)
  02_data_preparation/           tablas ya preparadas: tmdb.csv, catalog.csv (regenerables, git-ignored)
01_data_understanding/
  config.py      paths y carga de .env
  tmdb_data.py   cliente de TMDB + descarga del JSON crudo (recolectar, sin modificar)
  exploration.py análisis exploratorio (one-off)
  collect_initial_data/tmdb/   recolección del catálogo del MVP + refresh_log.md
02_data_preparation/
  prepare_tmdb.py  JSON crudo de TMDB -> tabla (format + integrate data)
  features.py    matriz de features (IMDb + TMDB); build() y build_row() (1 título)
  curate.py      marcar como vista o "no me interesa" (make watched / make skip)
  build_catalog.py  catálogo del sitio público (MVP)
03_modeling/                     las 3 tareas de modelado de CRISP-DM, un archivo cada una
  test_design.py   Generate test design: objetivo (nota >= 7), CV, bases a superar, métricas, bootstrap
  build_model.py   Build model: pipeline, entrenar/guardar, puntuar (watchlist, vistos, catálogo), predecir un título
  assess_model.py  Assess model: comparar modelos, curva de aprendizaje, trayectoria y prueba de robustez
  models/          modelos entrenados (git-ignored)
04_evaluation/     narrativa de la evaluación contra los criterios de éxito (evaluation.md)
05_deployment/
  build_results.py  datos de la página Proyecto de la web (make results)
  dashboard.py   generar el dashboard personal (data/05_deployment/, no se publica)
docs/            el sitio publicado por Pages: HTML + css/ + js/ + data/ + media/ (sin .md)
```

La metodología sigue CRISP-DM; cada fase está documentada y tiene su código en la carpeta numerada de su fase
(`00_business_understanding/` … `05_deployment/`, con la narrativa del proyecto personal en `<fase>.md` y el README del MVP). Cada script se puede correr directo
(`python 03_modeling/build_model.py`) o con `make`.

## Estado actual

- Mejor regresión: RandomForest sobre el desvío vs IMDb, **MAE 1.26** (baseline 1.31).
- Mejor binario (≥7): Gradient Boosting, **ROC AUC 0.63** (baseline 0.50).
- Cuello de botella: cantidad de datos (126 títulos puntuados). La curva de
  aprendizaje no saturó → más ratings es la mejora con mejor retorno. Ver
  [`03_modeling/modeling.md`](03_modeling/modeling.md).

## Links

- Datos: https://www.imdb.com/user/p.uwndhvvnyyx5vbgle5q7rfxsfy/ratings/
- API TMDB: https://www.themoviedb.org/settings/api (token v4 → `.env`)
- Deploy: https://nachomondino1.github.io/recommend_movie/
