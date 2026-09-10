# recommend_movie

Recomendador personal de películas y series: entrena con las notas que puse en
IMDb y predice qué nota le pondría a un título que todavía no vi, para priorizar
la watchlist.

## Objetivo
Aprendizaje supervisado. Variable respuesta: `Your Rating` (1–10 en IMDb).
Dos formulaciones: regresión de la nota y clasificación binaria "me gustó" (≥ 7).

## Estructura (CRISP-DM)
| Carpeta | Fase | Contenido |
|---|---|---|
| `docs/` | — | Documentación por fase (`1_business_understanding.md` … `6_deployment.md`) |
| `data/raw/` | — | Exportaciones de IMDb: `ratings.csv`, `watchlist.csv` |
| `data/external/`, `data/processed/` | — | Caché de TMDB y tablas derivadas (git-ignored) |
| `data_understanding/` | Data Understanding | `eda.py` |
| `data_preparation/` | Data Preparation | `tmdb_client.py`, `enrich_tmdb.py`, `build_features.py` |
| `modeling/` | Modeling | `train.py` (actual) + `model.py`, `model_v2.py`, `classify.py` (iteraciones previas) |
| `deployment/` | Deployment | `predict_watchlist.py` |
| `common.py` | — | Paths compartidos y carga de `.env` |

## Setup
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env      # y completar TMDB_TOKEN
```

## Correr el pipeline
```bash
./venv/bin/python data_understanding/eda.py            # análisis exploratorio
./venv/bin/python data_preparation/enrich_tmdb.py      # baja datos de TMDB (cachea)
./venv/bin/python modeling/train.py                    # compara modelos con CV
./venv/bin/python deployment/predict_watchlist.py      # puntúa la watchlist
```

## Estado actual
- Mejor regresión: RandomForest sobre el desvío vs IMDb, MAE 1.26 (baseline 1.31).
- Mejor binario (≥7): Gradient Boosting, ROC AUC 0.63 (baseline 0.50).
- Cuello de botella: cantidad de datos (126 títulos). Ver `docs/4_modeling.md`.
