# Fase 1 — Entender y recolectar los datos

De dónde sale todo lo que muestra el sitio público (`docs/`).

## Fuente

**TMDB** (API v3): películas y series que están en streaming por suscripción en una región
(por defecto `AR`), con en qué plataforma está cada una. Además, `fetch_credits.py` baja el elenco y el equipo de cada título
(`data/01_data_understanding/tmdb/credits.jsonl`), que usa el análisis de la nota (ver `data_understanding.md`). El historial del usuario (IMDb) no se
recolecta acá: cada visitante lo trae de su cuenta y se procesa en su navegador.

## Cómo se actualiza

```bash
python3 01_data_understanding/collect_initial_data/tmdb/refresh_tmdb_data.py            # corrida normal
python3 01_data_understanding/collect_initial_data/tmdb/refresh_tmdb_data.py --dry-run  # solo muestra qué cambiaría
python3 01_data_understanding/verify_data_quality.py                                   # revisa cobertura
```

Opciones: `--region AR`, `--top 400` (títulos por plataforma y tipo, por popularidad), `--providers 20`,
`--min-votes 50`, `--max-age-days 30` (no re-pide el detalle de títulos más nuevos que eso).
Necesita `TMDB_TOKEN` en `.env`. Normalmente se corre todo junto con `./sync_data.sh`.

## Archivos

- `collect_initial_data/tmdb/tmdb_common.py` — cliente de TMDB: reintenta los 429 y **cuenta cada request** por endpoint.
- `collect_initial_data/tmdb/refresh_tmdb_data.py` — la recolección. Es incremental: solo pide el detalle de títulos nuevos o vencidos.
- `verify_data_quality.py` — cuenta títulos, cobertura de campos (en especial el id de IMDb) y títulos por plataforma.
- `refresh_log.md` — **registro de cada uso de la API de TMDB**: una fila por corrida real, escrita por el script (fecha, opciones, requests totales y por endpoint, títulos en catálogo, detalles pedidos, nuevos, con plataformas distintas, errores, duración).

## Datos crudos (gitignoreados, viven en esta máquina)

En `data/01_data_understanding/`:

- `tmdb_titles.jsonl` — una fila por título, con el vocabulario de TMDB (géneros, directores, id de IMDb, nota, votos, plataformas, `fecha_actualizacion`). Abrible con cualquier editor o `jq`.
- `tmdb_providers.json` — plataformas de la región, en orden de relevancia.
- `tmdb_genres.json` — id → nombre de género.

> Las llamadas a la API salen solo de estos scripts. El sitio no llama a TMDB, así que el log es el registro completo.
