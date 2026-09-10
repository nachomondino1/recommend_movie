"""
Configuración compartida por todas las fases del proyecto.

Cada script agrega la raíz del repo a sys.path y hace:
    from common import RATINGS_CSV, TMDB_DIR, ...
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# --- Datos ---
DATA = ROOT / "data"
RAW = DATA / "raw"
EXTERNAL = DATA / "external"
PROCESSED = DATA / "processed"
OUTPUTS = ROOT / "outputs"

RATINGS_CSV = RAW / "ratings.csv"
WATCHLIST_CSV = RAW / "watchlist.csv"
TMDB_DIR = EXTERNAL / "tmdb"  # un JSON por título, cacheado

for _d in (PROCESSED, OUTPUTS, TMDB_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# --- Credenciales ---
def _load_dotenv() -> None:
    """Carga pares CLAVE=valor de un archivo .env en la raíz, sin dependencias."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

TMDB_TOKEN = os.environ.get("TMDB_TOKEN", "")
