# 2. Data Understanding

## Versión 2 (la actual): catálogo de TMDB, una sola fuente
Solo se recolecta y se describe: los datos quedan crudos.

| Archivo | Filas | Descripción |
|---|---|---|
| `data/01_data_understanding/tmdb/tmdb_titles.jsonl` | 8.493 | Una fila por título del catálogo (películas y series de las plataformas disponibles en Argentina): nota y votos de TMDB, géneros, director, duración, sinopsis, plataformas. Lo baja `refresh_tmdb_data.py`. |
| `data/01_data_understanding/tmdb/credits.jsonl` | 8.493 | Elenco principal (15), directores, guionistas, compositor y director de fotografía de cada título. Lo baja `fetch_credits.py`. |
| `tmdb_providers.json`, `tmdb_genres.json` | — | Plataformas y géneros de TMDB (vocabulario). |

De los 8.493 títulos (5.805 películas y 2.688 series), **6.774** tienen al menos 100 votos y entran al
análisis: con menos votos la nota de TMDB es muy ruidosa. (Los resultados casi no cambian si se usan los 8.493: R² 0,60 contra 0,61.)

### Variable respuesta
`vote_average`: la nota pública de TMDB (1 a 10). Entre los títulos analizados, promedio 6.92 y desvío 0.96.
Las películas promedian 6.59 (desvío 0.89) y las series 7.70 (desvío 0.62).
50 % de los títulos tiene 7 o más.

### Calidad
Parte de los títulos con cada dato: duración 88 %, director 92 %, sinopsis 96 %, elenco 99 %.
Lo que falta se completa en la preparación y en el modelo.

### Variables que se construyen después
Formato, duración, año, géneros, director, elenco, equipo, plataformas y largo de la sinopsis: ver
`02_data_preparation/data_preparation.md`. La popularidad y los votos de cada título se dejan aparte porque dependen de la nota.

---

## Versión 1 (archivada): la nota personal
En esa versión la fuente eran las exportaciones de IMDb de una persona, enriquecidas con TMDB.

| Archivo | Filas | Descripción |
|---|---|---|
| `data/01_data_understanding/imdb/ratings.csv` | 126 | Exportación de IMDb: títulos vistos y puntuados. Columna objetivo: `Your Rating`. |
| `data/01_data_understanding/imdb/watchlist.csv` | ~172 | Exportación de IMDb: títulos por ver (sin nota). |
| `data/01_data_understanding/tmdb/titles/*.json` | ~288 | Detalle crudo de TMDB solo de esos títulos (127 notas + 172 de la watchlist, sin repetidos). |
| `data/02_data_preparation/tmdb.csv` | ~288 | Esos 288 títulos aplanados (`prepare_tmdb.py`). **No se usa en la versión 2.** |

## Columnas de ratings.csv
`Const` (id IMDb), `Your Rating` (1–10), `Date Rated`, `Title`, `Title Type`
(Movie / TV Series / TV Mini Series), `IMDb Rating`, `Runtime (mins)`, `Year`,
`Genres` (lista separada por comas), `Num Votes`, `Release Date`, `Directors`.

## Hallazgos del EDA (`01_data_understanding/exploration.py`, `make explore`)
- **Distribución de `Your Rating`:** media 5.94, mediana 6, concentrada en 5–7.
  Solo 2 nueves, ningún diez. 24 títulos con nota ≤ 4.
- **Usuario vs IMDb:** promedia 1.48 puntos por debajo de IMDb. Correlación 0.29.
- **Correlaciones con la nota (débiles todas):** IMDb 0.29, Num Votes 0.16,
  Year −0.15, Runtime 0.08.
- **Por tipo:** Movie 6.01, TV Series 5.72, TV Mini Series 6.20 (casi no discrimina).
- **Por década:** 2020s 5.55 vs 2010s 6.46 (más crítico con lo reciente).
- **Por género (pocos casos por clase, tomar con pinzas):** arriba Documental,
  Biografía, Historia, Música, Guerra (~6.5–7); abajo Reality-TV, Crimen,
  Thriller (~4.8–5.4).
- **Faltantes:** `Directors` 46, `Runtime (mins)` 3, resto completo.

## Conclusión
Los metadatos de IMDb tienen poca señal sobre el gusto del usuario. Hace falta
describir el *contenido* (sinopsis, temas, elenco) → fuente TMDB.
