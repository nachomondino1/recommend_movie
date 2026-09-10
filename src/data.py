"""
CRISP-DM: Data Understanding + Data Preparation (parte 1).

- Carga las exportaciones de IMDb (ratings.csv, watchlist.csv).
- Enriquece cada título con datos de TMDB (sinopsis, keywords, elenco, director,
  idioma, métricas) y los cachea en data/cache/.

    python -m src.data          # descarga/actualiza data/cache/tmdb.csv
"""

import json
import time
from functools import lru_cache

import pandas as pd
import requests

from src.config import RATINGS_CSV, TMDB_CSV, TMDB_DIR, TMDB_TOKEN, WATCHLIST_CSV

BASE = "https://api.themoviedb.org/3"
TOP_CAST = 8


# --------------------------------------------------------------------------- #
# Carga de CSVs de IMDb
# --------------------------------------------------------------------------- #
def load_ratings() -> pd.DataFrame:
    return pd.read_csv(RATINGS_CSV)


def load_watchlist() -> pd.DataFrame:
    return pd.read_csv(WATCHLIST_CSV)


# --------------------------------------------------------------------------- #
# Cliente TMDB
# --------------------------------------------------------------------------- #
class TMDBError(RuntimeError):
    pass


class TMDBClient:
    """find(imdb_id) -> detalle crudo, cacheado en data/cache/tmdb/{id}.json."""

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
            return json.loads(cache.read_text())

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

        detail = self._get(f"/{media_type}/{tmdb_id}", append_to_response="credits,keywords")
        detail.update(imdb_id=imdb_id, media_type=media_type, tmdb_found=True)
        cache.write_text(json.dumps(detail, ensure_ascii=False))
        return detail


# --------------------------------------------------------------------------- #
# Aplanado del JSON de TMDB a fila tabular
# --------------------------------------------------------------------------- #
def _join(values, sep="|") -> str:
    return sep.join(str(v) for v in values if v)


def _parse(detail: dict) -> dict:
    if not detail.get("tmdb_found"):
        return {"imdb_id": detail.get("imdb_id"), "tmdb_found": False}

    mt = detail.get("media_type")
    credits = detail.get("credits", {})
    cast = [c["name"] for c in credits.get("cast", [])[:TOP_CAST]]
    if mt == "movie":
        directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
        runtime = detail.get("runtime")
    else:
        directors = [p["name"] for p in detail.get("created_by", [])]
        ert = detail.get("episode_run_time") or []
        runtime = ert[0] if ert else None
    kw = detail.get("keywords", {})
    keywords = [k["name"] for k in (kw.get("keywords") or kw.get("results") or [])]

    return {
        "imdb_id": detail["imdb_id"],
        "tmdb_found": True,
        "media_type": mt,
        "tmdb_title": detail.get("title") or detail.get("name"),
        "overview": detail.get("overview") or "",
        "tmdb_genres": _join(g["name"] for g in detail.get("genres", [])),
        "keywords": _join(keywords),
        "cast_top": _join(cast),
        "director": _join(directors),
        "tmdb_runtime": runtime,
        "original_language": detail.get("original_language"),
        "countries": _join(c["iso_3166_1"] for c in detail.get("production_countries", [])),
        "tmdb_vote_average": detail.get("vote_average"),
        "tmdb_vote_count": detail.get("vote_count"),
        "tmdb_popularity": detail.get("popularity"),
        "budget": detail.get("budget"),
        "revenue": detail.get("revenue"),
        "n_seasons": detail.get("number_of_seasons"),
        "n_episodes": detail.get("number_of_episodes"),
        "release_date": detail.get("release_date") or detail.get("first_air_date"),
    }


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #
def enrich(force: bool = False) -> pd.DataFrame:
    """Resuelve todos los títulos de ratings + watchlist y escribe data/cache/tmdb.csv."""
    ids = sorted(set(load_ratings()["Const"].dropna()) | set(load_watchlist()["Const"].dropna()))
    client = TMDBClient()
    print(f"Títulos únicos a resolver: {len(ids)}")

    rows, missing = [], []
    for i, imdb_id in enumerate(ids, 1):
        row = _parse(client.fetch(imdb_id, force=force))
        rows.append(row)
        if not row["tmdb_found"]:
            missing.append(imdb_id)
        if i % 25 == 0 or i == len(ids):
            print(f"  {i}/{len(ids)}")

    df = pd.DataFrame(rows)
    df.to_csv(TMDB_CSV, index=False)
    print(f"\nGuardado: {TMDB_CSV}  ({len(df)} filas)")
    print(f"Sin match en TMDB: {len(missing)}  {missing or ''}")
    for col in ("overview", "keywords", "cast_top", "director"):
        n = (df[col].fillna("").astype(str).str.len() > 0).sum()
        print(f"  cobertura {col:15s}: {n}/{len(df)}")
    return df


@lru_cache(maxsize=1)
def tmdb_table() -> pd.DataFrame:
    """data/cache/tmdb.csv como DataFrame (lo genera enrich() si falta)."""
    if not TMDB_CSV.exists():
        enrich()
    return pd.read_csv(TMDB_CSV)


if __name__ == "__main__":
    enrich()
