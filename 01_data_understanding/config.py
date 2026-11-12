"""
Paths del proyecto y carga de credenciales.

    from config import RATINGS_CSV, TMDB_TOKEN, ...
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATA = ROOT / "data"
TMDB_DIR = DATA / "01_data_understanding" / "tmdb" / "titles"   # JSON crudo de TMDB, un archivo por título
PREP_DIR = DATA / "02_data_preparation"       # tablas ya preparadas (regenerables)
MODELS = ROOT / "03_modeling" / "models"   # modelos entrenados -> gitignored
PLOTS_DIR = DATA / "01_data_understanding" / "exploration"   # gráficos del análisis exploratorio
MODELING_DIR = DATA / "03_modeling"            # puntuaciones, gráficos y métricas del modelado
DEPLOY_DIR = DATA / "05_deployment"            # dashboard personal generado
DOCS = ROOT / "docs"

IMDB_DIR = DATA / "01_data_understanding" / "imdb"   # tus exports de IMDb y lo que curás a mano
RATINGS_CSV = IMDB_DIR / "ratings.csv"
WATCHLIST_CSV = IMDB_DIR / "watchlist.csv"
EXCLUDED_CSV = IMDB_DIR / "excluded.csv"    # "no me interesa": Const + fecha
REVIEWS_CSV = IMDB_DIR / "reviews.csv"      # reseña personal (texto libre) por título
TMDB_CSV = PREP_DIR / "tmdb.csv"
CATALOG_CSV = PREP_DIR / "catalog.csv"          # Fase 6: catálogo ampliado, fuera de ratings/watchlist
SCORED_CSV = MODELING_DIR / "watchlist_scored.csv"
CATALOG_SCORED_CSV = MODELING_DIR / "catalog_scored.csv"
WATCHED_SCORED_CSV = MODELING_DIR / "watched_scored.csv"  # todos los títulos ya vistos (ratings.csv)
METRICS_CSV = MODELING_DIR / "metrics_history.csv"   # trayectoria real de scores

for _d in (PREP_DIR, TMDB_DIR, MODELS, IMDB_DIR, PLOTS_DIR, MODELING_DIR, DEPLOY_DIR):
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
