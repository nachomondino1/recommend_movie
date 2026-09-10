# 2. Data Understanding

## Fuentes
| Archivo | Filas | Descripción |
|---|---|---|
| `data/raw/ratings.csv` | 126 | Exportación de IMDb: títulos vistos y puntuados. Columna objetivo: `Your Rating`. |
| `data/raw/watchlist.csv` | 159 | Exportación de IMDb: títulos por ver (sin nota). Es el set sobre el que se predice al final. |
| `data/external/tmdb/*.json` | ~285 | Detalle crudo de TMDB por título (caché). |
| `data/processed/tmdb.csv` | ~285 | Campos de TMDB aplanados: sinopsis, keywords, elenco, director, idioma, país, etc. |

## Columnas de ratings.csv
`Const` (id IMDb), `Your Rating` (1–10), `Date Rated`, `Title`, `Title Type`
(Movie / TV Series / TV Mini Series), `IMDb Rating`, `Runtime (mins)`, `Year`,
`Genres` (lista separada por comas), `Num Votes`, `Release Date`, `Directors`.

## Hallazgos del EDA (`data_understanding/eda.py`)
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
