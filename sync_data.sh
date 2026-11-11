#!/bin/bash
# Actualiza el catálogo del sitio público: recolecta de TMDB, lo prepara, verifica y commitea en staging.
# Cada corrida suma una fila a 01_data_understanding/refresh_log.md. Producción (prod) se promueve
# aparte con un pull request (05_deployment/README.md).
#
# Uso: ./sync_data.sh                  (corrida normal)
#      ./sync_data.sh --top 800        (cualquier argumento va tal cual a refresh_tmdb_data.py)
set -euo pipefail
cd "$(dirname "$0")"

if [ "$(git branch --show-current)" != "staging" ]; then
  echo "Este script commitea en staging y ahora estás en '$(git branch --show-current)'. Cambiá de rama y volvé a correrlo." >&2
  exit 1
fi

PY=./venv/bin/python
[ -x "$PY" ] || PY=python3

echo "== Recolectando de TMDB =="
$PY 01_data_understanding/collect_initial_data/tmdb/refresh_tmdb_data.py "$@"

echo "== Verificando calidad =="
$PY 01_data_understanding/verify_data_quality.py

echo "== Armando el catálogo del sitio =="
$PY 02_data_preparation/build_catalog.py

git add docs/data 01_data_understanding/refresh_log.md
if git diff --cached --quiet; then
  echo "== Sin cambios, nada que commitear =="
else
  echo "== Commiteando y pusheando a staging =="
  git commit -m "Sync catálogo TMDB"
  git push origin staging
  echo "== Listo en staging. Para producción: pull request staging -> prod (05_deployment/README.md) =="
fi
