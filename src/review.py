"""
CRISP-DM: Deployment -- reseña personal de un título: qué te gustó y qué no.

    make review TITLE="Silo" LIKED="personajes bien marcados..." DISLIKED="muy lenta..."

    python -m src.review "Silo" --liked "..." --disliked "..."

Resuelve el título por nombre vía TMDB (igual que src.curate) y guarda/actualiza una
fila en data/reviews.csv (Const, Title, Liked, Disliked, Date) -- si ya había una
reseña para ese título, la reemplaza. Al menos uno de los dos campos tiene que tener
contenido (no hace falta completar ambos). No hace falta que el título esté puntuado
ni en la watchlist. Después de usar esto, correr 'make update' para que el dashboard
la muestre, y 'make eval' para ver qué palabras aparecen más en lo que te gusta vs lo
que no, juntando todas tus reseñas.
"""

import argparse
from datetime import date

import pandas as pd

from src.config import REVIEWS_CSV
from src.data import TMDBClient

REVIEWS_COLUMNS = ["Const", "Title", "Liked", "Disliked", "Date"]


def write_review(name: str, liked: str, disliked: str) -> dict:
    liked, disliked = liked.strip(), disliked.strip()
    if not liked and not disliked:
        raise SystemExit("La reseña no puede estar vacía (LIKED y DISLIKED vacíos).")

    detail = TMDBClient().fetch_by_name(name)
    imdb_id = detail.get("imdb_id")
    if not imdb_id:
        raise SystemExit(f"TMDB no devolvió un imdb_id para {name!r}; no se puede registrar.")
    title = detail.get("title") or detail.get("name")

    reviews = pd.read_csv(REVIEWS_CSV) if REVIEWS_CSV.exists() else pd.DataFrame(columns=REVIEWS_COLUMNS)
    replacing = imdb_id in set(reviews["Const"])
    reviews = reviews[reviews["Const"] != imdb_id]
    row = {"Const": imdb_id, "Title": title, "Liked": liked, "Disliked": disliked,
           "Date": date.today().isoformat()}
    reviews = pd.concat([reviews, pd.DataFrame([row])[REVIEWS_COLUMNS]], ignore_index=True)
    reviews.to_csv(REVIEWS_CSV, index=False)
    print(f"{'Actualizada' if replacing else 'Guardada'} la reseña de {title!r}.")
    print("Corré 'make update' para que se vea en el dashboard.")
    return row


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("title")
    ap.add_argument("--liked", default="")
    ap.add_argument("--disliked", default="")
    args = ap.parse_args()
    write_review(args.title, args.liked, args.disliked)


if __name__ == "__main__":
    main()
