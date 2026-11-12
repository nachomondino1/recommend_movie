"""
Cliente TMDB compartido por los scripts de recolección del MVP público.

Cuenta cada request por tipo de endpoint (para el log en refresh_log.md) y reintenta
los 429 respetando Retry-After. El token sale de TMDB_TOKEN (.env o variable de entorno).
"""

import os
import threading
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
DATA_RAW = ROOT / "data" / "01_data_understanding"
DATA_PREPARED = ROOT / "data" / "02_data_preparation"
REFRESH_LOG = ROOT / "01_data_understanding" / "refresh_log.md"
TMDB_RAW = DATA_RAW / "tmdb"   # lo crudo de TMDB para el catálogo del sitio
TITLES_JSONL = TMDB_RAW / "tmdb_titles.jsonl"
PROVIDERS_JSON = TMDB_RAW / "tmdb_providers.json"
GENRES_JSON = TMDB_RAW / "tmdb_genres.json"

BASE = "https://api.themoviedb.org/3"


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class TMDBError(RuntimeError):
    pass


class TMDBClient:
    """get(path, **params) -> dict. Thread-safe; cuenta requests por endpoint."""

    def __init__(self, token: str | None = None, pause: float = 0.02):
        load_dotenv()
        token = token or os.environ.get("TMDB_TOKEN", "")
        if not token:
            raise TMDBError("Falta TMDB_TOKEN (revisá el archivo .env)")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "accept": "application/json"})
        self.pause = pause
        self.calls = Counter()
        self.errors = Counter()
        self._lock = threading.Lock()

    @staticmethod
    def _endpoint_kind(path: str) -> str:
        parts = [p for p in path.split("/") if p and not p.isdigit()]
        return "/".join(parts[:2]) if parts else path

    def _request(self, path: str, params: dict) -> requests.Response:
        return self.session.get(f"{BASE}{path}", params=params, timeout=30)

    def get(self, path: str, **params) -> dict:
        kind = self._endpoint_kind(path)
        for _ in range(6):
            with self._lock:
                self.calls[kind] += 1
            r = self._request(path, params)
            if r.status_code == 429:
                with self._lock:
                    self.errors["429"] += 1
                time.sleep(int(r.headers.get("Retry-After", 2)))
                continue
            if r.status_code == 404:
                return {}
            if r.status_code >= 400:
                with self._lock:
                    self.errors[str(r.status_code)] += 1
                r.raise_for_status()
            time.sleep(self.pause)
            return r.json()
        raise TMDBError(f"Rate limit persistente en {path}")

    @property
    def total_calls(self) -> int:
        return sum(self.calls.values())
