"""
Fase 1 (CRISP-DM) - Verificar la calidad de los datos recolectados de TMDB.

    python3 01_data_understanding/verify_data_quality.py

Cuenta títulos, cobertura de campos clave y títulos por plataforma. Sale con código 1 si la
cobertura de id de IMDb (necesaria para cruzar con el historial del usuario) es menor al 80%.
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "collect_initial_data" / "tmdb"))
from tmdb_common import TITLES_JSONL  # noqa: E402


def pct(n: int, total: int) -> str:
    return f"{n} ({n / total:.0%})" if total else "0"


def main() -> None:
    if not TITLES_JSONL.exists():
        sys.exit("No hay datos todavía: corré refresh_tmdb_data.py primero.")
    rows = [json.loads(line) for line in TITLES_JSONL.read_text().split("\n") if line.strip()]
    live = [r for r in rows if r.get("providers")]
    n = len(live)
    print(f"Títulos en el archivo: {len(rows)} | con plataforma hoy: {n}")
    print(f"  películas: {sum(r['media_type'] == 'movie' for r in live)} | series: {sum(r['media_type'] == 'tv' for r in live)}")
    for field in ("imdb_id", "poster_path", "overview", "year", "genres", "directors", "vote_average"):
        print(f"  con {field:13s}: {pct(sum(1 for r in live if r.get(field)), n)}")
    per_provider = Counter(p for r in live for p in r["providers"])
    print("Títulos por plataforma:")
    for name, c in per_provider.most_common():
        print(f"  {name:28s} {c}")
    imdb_cov = sum(1 for r in live if r.get("imdb_id")) / n if n else 0
    if imdb_cov < 0.8:
        print("!! Menos del 80% de los títulos tiene id de IMDb: el cruce con el historial va a fallar seguido.")
        sys.exit(1)


if __name__ == "__main__":
    main()
