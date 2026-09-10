# 3. Data Preparation

## Pipeline
1. **`data_preparation/tmdb_client.py`** — cliente de la API de TMDB con caché a
   disco (`data/external/tmdb/{imdb_id}.json`). Resuelve `imdb_id → tmdb_id` con
   `/find` y baja el detalle con `append_to_response=credits,keywords`.
2. **`data_preparation/enrich_tmdb.py`** — junta los `Const` de ratings + watchlist
   (275 únicos), descarga todo y aplana a `data/processed/tmdb.csv`.
   Cobertura: sinopsis 274/275, keywords 268/275, elenco 273/275, director 260/275.
3. **`data_preparation/build_features.py`** — arma la matriz `X` (y `y` si hay notas).

## Features construidas
| Grupo | Columnas | Notas |
|---|---|---|
| Numéricas IMDb | IMDb Rating, Runtime, Year, log_votes, n_genres, years_since_release, is_franchise, runtime_missing | `years_since_release` no aplica a la watchlist (sin Date Rated) → se imputa. |
| Numéricas TMDB | tmdb_vote_average, log_tmdb_votes, tmdb_popularity, log_budget, n_seasons, n_episodes | |
| Categóricas (one-hot) | Title Type, lang_grouped (top 4 idiomas + "other"), media_type | |
| Target encoding | director (de TMDB, más completo que IMDb) | Se ajusta dentro de la CV (`TargetEncoder(cv=5)`) — sin leakage. |
| Texto | overview (sinopsis), keywords | Vectorizados dentro del pipeline: TF-IDF+SVD(25) para overview, CountVectorizer binario para keywords. |
| Multi-hot | genre_* (22, de IMDb) | |

## Decisiones y por qué
- **Vectorización dentro del pipeline de sklearn**, no en `build_features`, para que
  TF-IDF / SVD / TargetEncoder respeten los folds de la validación cruzada.
- **Imputación defensiva**: toda numérica que quede NaN se rellena con la mediana
  (los watchlist tienen IMDb Rating / Year faltantes en títulos sin estrenar).
- **`IMDb Rating` faltante** → se sustituye por `tmdb_vote_average`.

## Limitaciones conocidas
- La mediana de imputación se calcula por-llamada (train y watchlist usan medianas
  distintas). Impacto chico; a corregir si se productiviza.
- `years_since_release` en la watchlist queda imputado, no es un valor real.
