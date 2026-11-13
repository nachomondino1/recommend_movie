# 3. Data Preparation

## Versión 2 (la actual): `02_data_preparation/prepare_titles.py`
Toma el JSON crudo de TMDB (`tmdb_titles.jsonl` y `credits.jsonl`) y deja una fila por título en
`data/02_data_preparation/titles_features.csv` (8.493 filas).

| Tarea CRISP-DM | Qué se hace |
|---|---|
| Clean / Format | Un solo vocabulario de géneros: los de series se llevan al de películas (`Sci-Fi & Fantasy` → ciencia ficción + fantasía, etc.) y se descartan los que no aplican. Títulos duplicados fuera. |
| Construct | Un indicador 0/1 por género (18) y por plataforma (las 12 más frecuentes); cantidad de títulos del director; largo de la sinopsis; popularidad del elenco, cuántos son muy conocidos y cuántos títulos suman; ids de elenco y equipo para codificarlos en el modelo. |
| Select | Popularidad y cantidad de votos del título quedan en un grupo aparte ("circulares"): dependen de la nota, no la explican. |

El director, el elenco y el equipo se transforman en el promedio de nota de sus *otros* títulos **dentro del modelo** (`drivers_model.py`),
solo con datos de entrenamiento y dejando afuera el propio título, para que su nota no se cuele en su propia variable.

---

## Versión 1 (archivada): preparación de la nota personal
`01_data_understanding/tmdb_data.py` + `02_data_preparation/prepare_tmdb.py` + `features.py`. Esa versión preparaba solo los
títulos de las exportaciones de IMDb (~288 únicos: 127 notas + 172 de la watchlist), por eso `tmdb.csv` tiene 288 filas. No se usa en la versión 2.

## Pipeline (`01_data_understanding/tmdb_data.py`, `02_data_preparation/features.py`)
1. **`01_data_understanding/tmdb_data.py` → `TMDBClient`** — cliente de la API de TMDB con caché a disco
   (`data/01_data_understanding/tmdb/titles/{imdb_id}.json`). Resuelve `imdb_id → tmdb_id` con `/find` y
   baja el detalle con `append_to_response=credits,keywords`.
2. **`prepare_tmdb.py` → `build_tmdb_table()`** (`make update`) — junta los `Const` de ratings +
   watchlist (~288 únicos), descarga todo y aplana a `data/02_data_preparation/tmdb.csv` (`prepare_tmdb.py`).
   Cobertura típica: sinopsis ~99%, keywords ~97%, elenco ~99%, director ~95%.
3. **`02_data_preparation/features.py` → `build()`** — arma la matriz `X` (y `y` si hay notas).

## Features construidas
| Grupo | Columnas | Notas |
|---|---|---|
| Numéricas IMDb | IMDb Rating, Runtime, Year, log_votes, n_genres, years_since_release, is_franchise, runtime_missing | `years_since_release` no aplica a la watchlist (sin Date Rated) → se imputa. |
| Numéricas TMDB | tmdb_vote_average, log_tmdb_votes, tmdb_popularity, log_budget, n_seasons, n_episodes | |
| Categóricas (one-hot) | Title Type, lang_grouped (top 4 idiomas + "other"), media_type | |
| Target encoding | director (de TMDB, más completo que IMDb) | Se ajusta dentro de la CV (`TargetEncoder` con `KFold` sembrado) — sin leakage y reproducible. |
| Texto | overview (sinopsis), keywords | Vectorizados dentro del pipeline: TF-IDF+SVD(25) para overview, CountVectorizer binario para keywords. |
| Multi-hot | genre_* (22, de IMDb) | |

## Decisiones y por qué
- **Vectorización dentro del pipeline de sklearn**, no en `build()`, para que
  TF-IDF / SVD / TargetEncoder respeten los folds de la validación cruzada.
- **Imputación defensiva**: toda numérica que quede NaN se rellena con la mediana
  (los watchlist tienen IMDb Rating / Year faltantes en títulos sin estrenar).
- **`IMDb Rating` faltante** → se sustituye por `tmdb_vote_average`.

## Limitaciones conocidas
- La mediana de imputación se calcula por-llamada (train y watchlist usan medianas
  distintas). Impacto chico; a corregir si se productiviza.
- `years_since_release` en la watchlist queda imputado, no es un valor real.
