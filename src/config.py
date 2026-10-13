"""
Paths del proyecto y carga de credenciales.

    from src.config import RATINGS_CSV, TMDB_TOKEN, ...
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
CACHE = DATA / "cache"          # TMDB (json + tabla), regenerable -> gitignored
TMDB_DIR = CACHE / "tmdb"       # un JSON por título
MODELS = ROOT / "models"        # modelos entrenados -> gitignored
OUTPUTS = ROOT / "outputs"      # gráficos y CSVs para mirar local -> gitignored
DOCS = ROOT / "docs"

RATINGS_CSV = DATA / "ratings.csv"
WATCHLIST_CSV = DATA / "watchlist.csv"
EXCLUDED_CSV = DATA / "excluded.csv"    # "no me interesa": Const + fecha, versionado
REVIEWS_CSV = DATA / "reviews.csv"      # reseña personal (texto libre) por título, versionado
TMDB_CSV = CACHE / "tmdb.csv"
CATALOG_CSV = CACHE / "catalog.csv"          # Fase 6: catálogo ampliado, fuera de ratings/watchlist
SCORED_CSV = OUTPUTS / "watchlist_scored.csv"
CATALOG_SCORED_CSV = OUTPUTS / "catalog_scored.csv"
WATCHED_SCORED_CSV = OUTPUTS / "watched_scored.csv"  # todos los títulos ya vistos (ratings.csv)
METRICS_CSV = DATA / "metrics_history.csv"   # versionado: trayectoria real de scores

for _d in (CACHE, TMDB_DIR, MODELS, OUTPUTS):
    _d.mkdir(parents=True, exist_ok=True)


def _load_dotenv() -> None:
    """Carga CLAVE=valor desde .env en la raíz, sin dependencias."""
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
