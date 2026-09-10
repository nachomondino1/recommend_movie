"""
Cliente mínimo de la API de TMDB (v3 endpoints, auth v4 con Bearer token).

Estrategia:
    1. /find/{imdb_id}  -> resuelve el id de TMDB y si es movie o tv
    2. /movie|tv/{id}?append_to_response=credits,keywords -> detalle completo

Cada respuesta cruda se cachea en data/external/tmdb/{imdb_id}.json, así se
puede re-parsear sin volver a llamar a la API.
"""

import json
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import TMDB_DIR, TMDB_TOKEN

BASE = "https://api.themoviedb.org/3"


class TMDBError(RuntimeError):
    pass


class TMDBClient:
    def __init__(self, token: str = TMDB_TOKEN, pause: float = 0.05):
        if not token:
            raise TMDBError("Falta TMDB_TOKEN (revisá el archivo .env)")
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "accept": "application/json"}
        )
        self.pause = pause

    def _get(self, path: str, **params) -> dict:
        url = f"{BASE}{path}"
        for attempt in range(5):
            r = self.session.get(url, params=params, timeout=30)
            if r.status_code == 429:  # rate limit
                wait = int(r.headers.get("Retry-After", 2))
                time.sleep(wait)
                continue
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            time.sleep(self.pause)
            return r.json()
        raise TMDBError(f"Rate limit persistente en {path}")

    def fetch(self, imdb_id: str, force: bool = False) -> dict:
        """Devuelve el detalle crudo de TMDB para un id de IMDb (tt...)."""
        cache = TMDB_DIR / f"{imdb_id}.json"
        if cache.exists() and not force:
            return json.loads(cache.read_text())

        found = self._get(f"/find/{imdb_id}", external_source="imdb_id")
        movie = found.get("movie_results") or []
        tv = found.get("tv_results") or []

        if movie:
            media_type, tmdb_id = "movie", movie[0]["id"]
        elif tv:
            media_type, tmdb_id = "tv", tv[0]["id"]
        else:
            data = {"imdb_id": imdb_id, "tmdb_found": False}
            cache.write_text(json.dumps(data))
            return data

        detail = self._get(
            f"/{media_type}/{tmdb_id}",
            append_to_response="credits,keywords",
        )
        detail["imdb_id"] = imdb_id
        detail["media_type"] = media_type
        detail["tmdb_found"] = True
        cache.write_text(json.dumps(detail, ensure_ascii=False))
        return detail


if __name__ == "__main__":
    # Prueba rápida: Interstellar
    client = TMDBClient()
    d = client.fetch("tt0816692", force=True)
    print("found:", d.get("tmdb_found"), "| type:", d.get("media_type"))
    print("title:", d.get("title") or d.get("name"))
    print("overview:", (d.get("overview") or "")[:120], "...")
    kw = d.get("keywords", {})
    kws = kw.get("keywords") or kw.get("results") or []
    print("keywords:", [k["name"] for k in kws][:8])
    cast = d.get("credits", {}).get("cast", [])
    print("cast:", [c["name"] for c in cast[:5]])
