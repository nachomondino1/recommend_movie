"""
Fase 1 (CRISP-DM) - Recolección: trae de TMDB el catálogo de películas y series que
están en streaming (suscripción) en una región, con en qué plataforma está cada una.

Cada corrida real suma una fila a 01_data_understanding/refresh_log.md con la cantidad de
requests a la API (total y por endpoint), cuántos títulos cambiaron, nuevos, errores y duración.

    python3 01_data_understanding/collect_initial_data/tmdb/refresh_tmdb_data.py
    python3 ... --top 800 --providers 25      # más profundo (más requests)
    python3 ... --dry-run                     # muestra qué cambiaría, sin escribir nada

Necesita TMDB_TOKEN en .env. Salida: data/01_data_understanding/tmdb_titles.jsonl (una fila
por título), tmdb_providers.json y tmdb_genres.json. El catálogo del sitio se arma en la
fase 2 (02_data_preparation/build_catalog.py).
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tmdb_common import (DATA_RAW, GENRES_JSON, PROVIDERS_JSON, REFRESH_LOG,  # noqa: E402
                         TITLES_JSONL, TMDBClient)

MEDIA_TYPES = ("movie", "tv")
LOG_HEADER = (
    "# Registro de actualizaciones de TMDB\n\n"
    "Una fila por cada corrida real de `refresh_tmdb_data.py` (la escribe el script solo, no a mano). "
    "\"Requests\" es el total de llamadas a la API de TMDB de esa corrida.\n\n"
    "| Fecha | Opciones | Requests | Por endpoint | Títulos en catálogo | Detalles pedidos | Nuevos "
    "| Con plataformas distintas | Errores | Duración |\n"
    "|---|---|---|---|---|---|---|---|---|---|\n"
)


def key_of(media_type: str, tmdb_id: int) -> str:
    return f"{media_type}:{tmdb_id}"


def fetch_providers(client, region: str, n: int) -> list[dict]:
    by_id = {}
    for mt in MEDIA_TYPES:
        res = client.get(f"/watch/providers/{mt}", watch_region=region)
        for p in res.get("results", []):
            by_id.setdefault(p["provider_id"], p)
    ranked = sorted(by_id.values(), key=lambda p: (p.get("display_priorities") or {}).get(region, 999))
    return [{"id": p["provider_id"], "name": p["provider_name"], "logo": p.get("logo_path")}
            for p in ranked[:n]]


def fetch_genres(client) -> dict:
    out = {}
    for mt in MEDIA_TYPES:
        for g in client.get(f"/genre/{mt}/list", language="en").get("genres", []):
            out[str(g["id"])] = g["name"]
    return out


def discover_pair(client, region, provider_id, media_type, top, min_votes) -> list[dict]:
    """Los `top` títulos más populares de una plataforma (suscripción) para un tipo."""
    out, page = [], 1
    while len(out) < top and page <= 40:
        res = client.get(
            f"/discover/{media_type}", watch_region=region, with_watch_providers=provider_id,
            with_watch_monetization_types="flatrate", sort_by="popularity.desc",
            **{"vote_count.gte": min_votes}, page=page, language="es")
        results = res.get("results") or []
        if not results:
            break
        out.extend(dict(r, media_type=media_type) for r in results)
        page += 1
    return out[:top]


def make_row(media_type: str, basic: dict, detail: dict) -> dict:
    credits = detail.get("credits") or {}
    if media_type == "movie":
        directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
        runtime = detail.get("runtime")
    else:
        directors = [p["name"] for p in detail.get("created_by", [])]
        ert = detail.get("episode_run_time") or []
        runtime = ert[0] if ert else None
    imdb_id = (detail.get("external_ids") or {}).get("imdb_id") or detail.get("imdb_id") or None
    release = detail.get("release_date") or detail.get("first_air_date") \
        or basic.get("release_date") or basic.get("first_air_date") or ""
    return {
        "tmdb_id": basic["id"],
        "media_type": media_type,
        "imdb_id": imdb_id,
        "title": detail.get("title") or detail.get("name") or basic.get("title") or basic.get("name"),
        "original_title": detail.get("original_title") or detail.get("original_name"),
        "year": int(release[:4]) if release[:4].isdigit() else None,
        "genres": [g["name"] for g in detail.get("genres", [])],
        "genre_ids": [g["id"] for g in detail.get("genres", [])],
        "directors": directors,
        "vote_average": detail.get("vote_average", basic.get("vote_average")),
        "vote_count": detail.get("vote_count", basic.get("vote_count")),
        "popularity": basic.get("popularity"),
        "poster_path": detail.get("poster_path") or basic.get("poster_path"),
        "overview": detail.get("overview") or basic.get("overview") or "",
        "runtime": runtime,
        "seasons": detail.get("number_of_seasons"),
        "fecha_actualizacion": date.today().isoformat(),
    }


def load_existing() -> dict:
    rows = {}
    if TITLES_JSONL.exists():
        for line in TITLES_JSONL.read_text().split("\n"):
            if line.strip():
                r = json.loads(line)
                rows[key_of(r["media_type"], r["tmdb_id"])] = r
    return rows


def is_stale(row: dict, max_age_days: int) -> bool:
    try:
        age = (date.today() - date.fromisoformat(row["fecha_actualizacion"])).days
    except (KeyError, ValueError):
        return True
    return age > max_age_days or not row.get("imdb_id") or "genre_ids" not in row


def fmt_duration(seconds: float) -> str:
    return f"{int(seconds // 60)} min {int(seconds % 60)} s"


def append_log(args, client, n_catalog, n_detail, n_new, n_changed, seconds) -> None:
    opts = f"`--region {args.region} --top {args.top} --providers {args.providers} --max-age-days {args.max_age_days}`"
    per_endpoint = ", ".join(f"{k}: {v}" for k, v in sorted(client.calls.items()))
    errors = ", ".join(f"{k}×{v}" for k, v in sorted(client.errors.items())) or "0"
    REFRESH_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not REFRESH_LOG.exists():
        REFRESH_LOG.write_text(LOG_HEADER)
    with REFRESH_LOG.open("a") as f:
        f.write(f"| {date.today().isoformat()} | {opts} | {client.total_calls} | {per_endpoint} | {n_catalog} "
                f"| {n_detail} | {n_new} | {n_changed} | {errors} | {fmt_duration(seconds)} |\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", default="AR", help="país (código ISO) para las plataformas")
    ap.add_argument("--top", type=int, default=400, help="títulos por plataforma y por tipo (por popularidad)")
    ap.add_argument("--providers", type=int, default=100, help="cantidad de plataformas a recorrer (100 = todas las de la región)")
    ap.add_argument("--min-votes", type=int, default=50, help="votos mínimos en TMDB para entrar")
    ap.add_argument("--max-age-days", type=int, default=30, help="no re-pedir el detalle de títulos más nuevos que esto")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true", help="no escribe archivos ni log")
    args = ap.parse_args()

    started = time.time()
    client = TMDBClient()
    existing = load_existing()

    providers = fetch_providers(client, args.region, args.providers)
    genres = fetch_genres(client)
    print(f"Plataformas: {', '.join(p['name'] for p in providers)}")

    # Qué títulos están en qué plataforma (esto se reconstruye entero en cada corrida)
    pairs = [(p, mt) for p in providers for mt in MEDIA_TYPES]
    with ThreadPoolExecutor(args.workers) as ex:
        found = list(ex.map(lambda pm: discover_pair(
            client, args.region, pm[0]["id"], pm[1], args.top, args.min_votes), pairs))
    membership, basics = {}, {}
    for (prov, mt), results in zip(pairs, found):
        for r in results:
            k = key_of(mt, r["id"])
            membership.setdefault(k, set()).add(prov["name"])
            basics.setdefault(k, r)
    print(f"Títulos en streaming en {args.region}: {len(membership)}")

    # Detalle (directores, imdb_id, runtime...) solo de los nuevos o vencidos
    todo = [k for k in membership if k not in existing or is_stale(existing[k], args.max_age_days)]

    def fetch(k):
        mt, tid = k.split(":")
        try:
            detail = client.get(f"/{mt}/{tid}", append_to_response="credits,external_ids", language="es")
        except Exception:
            client.errors["detalle"] += 1
            detail = {}
        return k, make_row(mt, basics[k], detail)

    n_new = sum(1 for k in todo if k not in existing)
    with ThreadPoolExecutor(args.workers) as ex:
        for i, (k, row) in enumerate(ex.map(fetch, todo), 1):
            row["providers"] = existing.get(k, {}).get("providers")  # para contar bien los cambios de plataforma
            existing[k] = row
            if i % 200 == 0 or i == len(todo):
                print(f"  detalle {i}/{len(todo)}")

    n_changed = 0
    for k, row in existing.items():
        new_providers = sorted(membership.get(k, []))
        if row.get("providers") != new_providers:
            n_changed += 1
        row["providers"] = new_providers
    n_catalog = sum(1 for r in existing.values() if r["providers"])

    elapsed = time.time() - started
    print(f"Listo: {n_catalog} títulos con plataforma, {len(todo)} detalles pedidos ({n_new} nuevos), "
          f"{n_changed} con plataformas distintas, {client.total_calls} requests, {fmt_duration(elapsed)}.")
    if args.dry_run:
        print("--dry-run: no se escribió nada.")
        return

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    tmp = TITLES_JSONL.with_suffix(".tmp")
    tmp.write_text("\n".join(json.dumps(existing[k], ensure_ascii=False) for k in sorted(existing)) + "\n")
    tmp.replace(TITLES_JSONL)
    PROVIDERS_JSON.write_text(json.dumps({"region": args.region, "providers": providers,
                                          "fecha_actualizacion": datetime.now().isoformat(timespec="seconds")},
                                         ensure_ascii=False, indent=1))
    GENRES_JSON.write_text(json.dumps(genres, ensure_ascii=False, indent=1))
    append_log(args, client, n_catalog, len(todo), n_new, n_changed, elapsed)
    print(f"Escrito: {TITLES_JSONL} y fila nueva en {REFRESH_LOG}")


if __name__ == "__main__":
    main()
