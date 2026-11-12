"""
CRISP-DM · Comprensión de los datos (recolectar, sin modificar): elenco y equipo de cada título del catálogo.

`refresh_tmdb_data.py` ya pedía los créditos pero se quedaba solo con los directores. Acá se bajan aparte, para poder
estudiar si el elenco, el guion o la música se asocian con la nota. Una fila por título en credits.jsonl (si se corta,
al volver a correr retoma donde quedó).

  - elenco  : los 15 primeros del reparto (id, nombre, orden, popularidad en TMDB)
  - equipo  : directores, guionistas, compositor y director de fotografía (id y nombre)

    python3 01_data_understanding/collect_initial_data/tmdb/fetch_credits.py [--workers 8] [--limit N]
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tmdb_common import TITLES_JSONL, TMDB_RAW, TMDBClient  # noqa: E402

CREDITS_JSONL = TMDB_RAW / "credits.jsonl"
TOP_CAST = 15
CREW_JOBS = {
    "directors": {"Director"},
    "writers": {"Screenplay", "Writer", "Story", "Novel", "Characters", "Creator"},
    "composers": {"Original Music Composer", "Composer"},
    "cinematographers": {"Director of Photography"},
}


def compact(credits: dict) -> dict:
    cast = [{"id": c["id"], "name": c["name"], "order": c.get("order"), "popularity": c.get("popularity")}
            for c in (credits.get("cast") or [])[:TOP_CAST]]
    crew = {k: [] for k in CREW_JOBS}
    for c in credits.get("crew") or []:
        for k, jobs in CREW_JOBS.items():
            if c.get("job") in jobs and not any(x["id"] == c["id"] for x in crew[k]):
                crew[k].append({"id": c["id"], "name": c["name"]})
    return {"cast": cast, **crew}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="solo los primeros N títulos (prueba)")
    args = ap.parse_args()

    titles = [json.loads(line) for line in TITLES_JSONL.open()]
    done = set()
    if CREDITS_JSONL.exists():
        done = {(r["media_type"], r["tmdb_id"]) for r in map(json.loads, CREDITS_JSONL.open())}
    todo = [t for t in titles if (t["media_type"], t["tmdb_id"]) not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(titles)} títulos · ya bajados {len(done)} · a bajar {len(todo)}", flush=True)

    client, t0, n = TMDBClient(), time.time(), 0

    def fetch(t):
        mt, tid = t["media_type"], t["tmdb_id"]
        return {"media_type": mt, "tmdb_id": tid, **compact(client.get(f"/{mt}/{tid}/credits", language="es"))}

    with CREDITS_JSONL.open("a") as out, ThreadPoolExecutor(args.workers) as ex:
        for row in ex.map(fetch, todo):
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            n += 1
            if n % 500 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)}  ({time.time() - t0:.0f} s, {client.total_calls} llamadas)", flush=True)
    print(f"Guardado: {CREDITS_JSONL}")


if __name__ == "__main__":
    main()
