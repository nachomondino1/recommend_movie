# Fase 2 — Preparar los datos

Convierte los datos crudos de TMDB en el catálogo que lee el sitio.

```bash
python3 02_data_preparation/build_catalog.py           # data/01_data_understanding/*.jsonl -> docs/mvp/data/catalog.json
python3 02_data_preparation/build_catalog.py --force   # salta el chequeo de 95%
```

## Qué hace `build_catalog.py`

- **Selecciona:** solo títulos con al menos una plataforma hoy y con título.
- **Construye:** pasa los géneros de TMDB al vocabulario de IMDb (`Science Fiction` → `Sci-Fi`, `Action & Adventure` → `Action` + `Adventure`, etc.) para poder cruzarlos con las notas del usuario; recorta la sinopsis a 220 caracteres; reemplaza los nombres de plataforma por ids.
- **Protege:** si el catálogo nuevo tiene menos del 95% de los títulos del actual, aborta (probable falla de la recolección) salvo que uses `--force`.

## Salida

`docs/mvp/data/catalog.json` (versionado, lo que publica el sitio): `generated`, `region`, `providers`, `titles`. Cada título: `id` (TMDB), `type` (`movie`/`tv`), `imdb`, `title`, `year`, `genres`, `directors`, `rating`, `votes`, `poster`, `overview`, `runtime`, `seasons`, `providers` (ids).

El cruce con el historial del usuario se hace en el navegador por `imdb` (`docs/mvp/js/catalog.js`).
