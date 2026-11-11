"""
Fase 2 (CRISP-DM) - Preparación: arma el catálogo que consume el sitio.

Lee data/01_data_understanding/tmdb_titles.jsonl (crudo, vocabulario de TMDB) y escribe
docs/data/catalog.json: solo títulos con plataforma, géneros pasados al vocabulario de
IMDb (para poder cruzarlos con las notas del usuario) y campos recortados al mínimo.

    python3 02_data_preparation/build_catalog.py
    python3 02_data_preparation/build_catalog.py --force   # salta el chequeo de 95% vs. el catálogo actual
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "01_data_understanding" / "collect_initial_data" / "tmdb"))
from tmdb_common import GENRES_JSON, PROVIDERS_JSON, TITLES_JSONL  # noqa: E402

CATALOG_JSON = ROOT / "docs" / "data" / "catalog.json"
OVERVIEW_MAX = 220
MIN_TITLES = 150  # plataformas con menos títulos que esto no entran al catálogo

# Plataformas que no son "dónde ver": canales que se contratan dentro de Amazon/Apple (duplican al servicio
# base), tiendas de compra/alquiler y agregadores. Editá esta lista para sumar o sacar.
EXCLUDED_PROVIDERS = re.compile(
    r"channel$|^Amazon Video$|^Apple TV Store$|JustWatch|^Plex$|Tencent|Bloodstream|Artiflix|Artify|Cultpix"
    r"|^Runtime$|Shahid|Takflix|Eventive|Univer Video|KableOne|Jolt|FOUND TV|CaixaForum", re.I)

# Vocabulario de TMDB -> vocabulario de IMDb ([] = se descarta)
GENRE_ALIASES = {
    "Science Fiction": ["Sci-Fi"], "Action & Adventure": ["Action", "Adventure"],
    "Sci-Fi & Fantasy": ["Sci-Fi", "Fantasy"], "War & Politics": ["War"], "Kids": ["Family"],
    "Reality": ["Reality-TV"], "Soap": [], "Talk": [], "News": [], "TV Movie": [],
}


def norm_genres(names: list[str]) -> list[str]:
    out = []
    for n in names:
        for g in GENRE_ALIASES.get(n, [n]):
            if g not in out:
                out.append(g)
    return out


def short(text: str) -> str:
    text = (text or "").strip()
    return text if len(text) <= OVERVIEW_MAX else text[:OVERVIEW_MAX].rsplit(" ", 1)[0] + "…"


def build() -> dict:
    meta = json.loads(PROVIDERS_JSON.read_text())
    allowed = [p for p in meta["providers"] if not EXCLUDED_PROVIDERS.search(p["name"])]
    id_by_name = {p["name"]: p["id"] for p in allowed}
    genre_en = json.loads(GENRES_JSON.read_text())  # id -> nombre en inglés (las fichas vienen en español)

    rows = [json.loads(line) for line in TITLES_JSONL.read_text().split("\n") if line.strip()]
    counts = Counter(id_by_name[n] for r in rows for n in set(r.get("providers", [])) if n in id_by_name)
    keep = {pid for pid, c in counts.items() if c >= MIN_TITLES}

    titles = []
    for r in rows:
        pids = sorted({id_by_name[n] for n in r.get("providers", []) if n in id_by_name} & keep)
        if not pids or not r.get("title"):
            continue
        titles.append({
            "id": r["tmdb_id"], "type": r["media_type"], "imdb": r.get("imdb_id"),
            "title": r["title"], "year": r.get("year"),
            "genres": norm_genres([genre_en[str(i)] for i in r["genre_ids"] if str(i) in genre_en]), "directors": r.get("directors", []),
            "rating": round(r["vote_average"], 1) if r.get("vote_average") else None,
            "votes": r.get("vote_count"), "poster": r.get("poster_path"),
            "overview": short(r.get("overview")), "runtime": r.get("runtime"),
            "seasons": r.get("seasons"), "providers": pids,
        })
    titles.sort(key=lambda t: -(t["votes"] or 0))
    providers = sorted((p for p in allowed if p["id"] in keep), key=lambda p: -counts[p["id"]])
    return {
        "generated": date.today().isoformat(), "region": meta["region"], "source": "TMDB",
        "providers": providers, "titles": titles,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    catalog = build()
    n = len(catalog["titles"])
    if CATALOG_JSON.exists() and not args.force:
        old = len(json.loads(CATALOG_JSON.read_text()).get("titles", []))
        if old and n < 0.95 * old:
            sys.exit(f"El catálogo nuevo tiene {n} títulos y el actual {old} (menos del 95%). "
                     "Revisá la recolección o corré con --force.")
    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_JSON.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")))
    size = CATALOG_JSON.stat().st_size / 1e6
    with_imdb = sum(1 for t in catalog["titles"] if t["imdb"])
    print(f"Catálogo: {n} títulos ({with_imdb} con id de IMDb), {len(catalog['providers'])} plataformas, "
          f"{size:.1f} MB -> {CATALOG_JSON}")


if __name__ == "__main__":
    main()
