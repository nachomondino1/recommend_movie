"""
CRISP-DM · Comprensión de los datos (recolectar, SIN modificar): cliente de TMDB y descarga del JSON crudo.

Acá solo se baja lo que TMDB devuelve para cada título de tus exportaciones de IMDb y se guarda tal cual
(un JSON por título en data/01_data_understanding/tmdb/titles/). Aplanarlo a una tabla, limpiarlo y
combinarlo es Preparación de datos: 02_data_preparation/prepare_tmdb.py.

    python 01_data_understanding/tmdb_data.py     # baja/actualiza el JSON crudo de cada título
"""

import sys
from pathlib import Path

sys.path[:0] = [str(d) for d in Path(__file__).resolve().parents[1].glob("0[1-5]_*")]


import json
import time

import pandas as pd
import requests

from config import RATINGS_CSV, TMDB_DIR, TMDB_TOKEN, WATCHLIST_CSV

BASE = "https://api.themoviedb.org/3"


# --------------------------------------------------------------------------- #
# Cliente TMDB
# --------------------------------------------------------------------------- #
class TMDBError(RuntimeError):
    pass


class TMDBClient:
    """find(imdb_id) -> detalle crudo, cacheado en data/01_data_understanding/tmdb/titles/{id}.json."""

    def __init__(self, token: str = TMDB_TOKEN, pause: float = 0.05):
        if not token:
            raise TMDBError("Falta TMDB_TOKEN (revisá el archivo .env)")
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}", "accept": "application/json"}
        )
        self.pause = pause

    def _get(self, path: str, **params) -> dict:
        for _ in range(5):
            r = self.session.get(f"{BASE}{path}", params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(int(r.headers.get("Retry-After", 2)))
                continue
            if r.status_code == 404:
                return {}
            r.raise_for_status()
            time.sleep(self.pause)
            return r.json()
        raise TMDBError(f"Rate limit persistente en {path}")

    def fetch(self, imdb_id: str, force: bool = False) -> dict:
        cache = TMDB_DIR / f"{imdb_id}.json"
        if cache.exists() and not force:
            data = json.loads(cache.read_text())
            if data.get("tmdb_found") and "providers_flatrate_ar" not in data:
                data["providers_flatrate_ar"] = self._providers(data["media_type"], data["id"])
                cache.write_text(json.dumps(data, ensure_ascii=False))
            return data

        found = self._get(f"/find/{imdb_id}", external_source="imdb_id")
        movie, tv = found.get("movie_results") or [], found.get("tv_results") or []
        if movie:
            media_type, tmdb_id = "movie", movie[0]["id"]
        elif tv:
            media_type, tmdb_id = "tv", tv[0]["id"]
        else:
            data = {"imdb_id": imdb_id, "tmdb_found": False}
            cache.write_text(json.dumps(data))
            return data
        return self._detail(media_type, tmdb_id, imdb_id)

    def _providers(self, media_type: str, tmdb_id: int) -> list[str]:
        """Plataformas de streaming por suscripción (AR), vía /watch/providers."""
        res = self._get(f"/{media_type}/{tmdb_id}/watch/providers")
        ar = (res.get("results") or {}).get("AR") or {}
        return [p["provider_name"] for p in ar.get("flatrate", [])]

    def _detail(self, media_type: str, tmdb_id: int, imdb_id: str | None) -> dict:
        detail = self._get(f"/{media_type}/{tmdb_id}",
                           append_to_response="credits,keywords,external_ids")
        imdb_id = imdb_id or (detail.get("external_ids") or {}).get("imdb_id")
        detail.update(imdb_id=imdb_id, media_type=media_type, tmdb_found=True)
        detail["providers_flatrate_ar"] = self._providers(media_type, tmdb_id)
        if imdb_id:
            (TMDB_DIR / f"{imdb_id}.json").write_text(json.dumps(detail, ensure_ascii=False))
        return detail

    def search(self, query: str) -> list[dict]:
        """Resultados de /search/multi filtrados a películas y series."""
        res = self._get("/search/multi", query=query, include_adult="false")
        return [r for r in res.get("results", []) if r.get("media_type") in ("movie", "tv")]

    def fetch_by_name(self, query: str) -> dict:
        """Busca por nombre y devuelve el detalle crudo del primer resultado."""
        hits = self.search(query)
        if not hits:
            raise TMDBError(f"TMDB no encontró nada para: {query!r}")
        top = hits[0]
        return self._detail(top["media_type"], top["id"], imdb_id=None)

    def discover(self, media_type: str, n: int, min_votes: int = 100) -> list[dict]:
        """IDs de /discover/{media_type} ordenados por popularidad, acotado a n
        (usado por build_model.py para armar el catálogo ampliado)."""
        out, page = [], 1
        while len(out) < n and page <= 20:
            res = self._get(f"/discover/{media_type}", page=page, sort_by="popularity.desc",
                            **{"vote_count.gte": min_votes})
            results = res.get("results") or []
            if not results:
                break
            out.extend({"media_type": media_type, "id": r["id"]} for r in results)
            page += 1
        return out[:n]

    def external_id(self, media_type: str, tmdb_id: int) -> str | None:
        """IMDb id de un título ya identificado en TMDB, vía /external_ids (liviano,
        no cachea: solo se usa para decidir si fetch_by_tmdb_id necesita pedir más)."""
        return (self._get(f"/{media_type}/{tmdb_id}/external_ids") or {}).get("imdb_id") or None

    def fetch_by_tmdb_id(self, media_type: str, tmdb_id: int) -> dict:
        """Como fetch(), pero arrancando desde un id de TMDB ya conocido (p. ej. de
        discover()), que no trae imdb_id de forma directa."""
        imdb_id = self.external_id(media_type, tmdb_id)
        if imdb_id and (TMDB_DIR / f"{imdb_id}.json").exists():
            return self.fetch(imdb_id)
        return self._detail(media_type, tmdb_id, imdb_id)


# --------------------------------------------------------------------------- #
# Recolección
# --------------------------------------------------------------------------- #
def collect_raw(force: bool = False) -> list[dict]:
    """Resuelve todos los títulos de ratings + watchlist y devuelve el JSON crudo de cada uno
    (lo baja si no está en la caché; no transforma nada)."""
    ids = sorted(set(pd.read_csv(RATINGS_CSV)["Const"].dropna()) | set(pd.read_csv(WATCHLIST_CSV)["Const"].dropna()))
    client = TMDBClient()
    print(f"Títulos únicos a resolver: {len(ids)}")
    raws = []
    for i, imdb_id in enumerate(ids, 1):
        raws.append(client.fetch(imdb_id, force=force))
        if i % 25 == 0 or i == len(ids):
            print(f"  {i}/{len(ids)}")
    return raws


if __name__ == "__main__":
    raws = collect_raw()
    print(f"JSON crudo en {TMDB_DIR}  ({sum(1 for r in raws if r.get('tmdb_found'))}/{len(raws)} con match en TMDB)")
