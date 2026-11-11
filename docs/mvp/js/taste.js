// Resumen del gusto a partir de las notas del usuario (port de src/taste.py).

const MIN_GENRE_N = 3, MIN_DIRECTOR_N = 2, TOP_DIRECTORS = 8, TOP_TITLES = 5;

function splitList(s) {
  return (s || "").split(",").map((x) => x.trim()).filter(Boolean);
}

// Une la fila del CSV de IMDb con el título del catálogo (si está).
function mergeRow(r, cat) {
  const c = cat || {};
  return {
    ...r,
    Genres: r.Genres || (c.genres || []).join(", "),
    Directors: r.Directors || (c.directors || []).join(", "),
    ImdbRating: r.ImdbRating ?? c.rating ?? null,
    Runtime: r.Runtime ?? c.runtime ?? null,
    poster_path: c.poster || null,
    overview: c.overview || "",
    providers: providerNames(c.providers || []),
    seasons: c.seasons || null,
  };
}

function groupAvg(rows, keysOf, minN) {
  const acc = new Map();
  for (const r of rows) {
    for (const k of keysOf(r)) {
      const a = acc.get(k) || { n: 0, sum: 0 };
      a.n++; a.sum += r.YourRating;
      acc.set(k, a);
    }
  }
  return [...acc.entries()]
    .filter(([, a]) => a.n >= minN)
    .map(([label, a]) => ({ label, n: a.n, avg: Math.round((a.sum / a.n) * 100) / 100 }))
    .sort((x, y) => y.avg - x.avg);
}

const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;

function buildTaste(rated) {
  if (!rated.length) return null;
  const withImdb = rated.filter((r) => r.ImdbRating != null);
  const sorted = [...rated].sort((a, b) => b.YourRating - a.YourRating);
  return {
    n_rated: rated.length,
    mean_rating: Math.round(mean(rated.map((r) => r.YourRating)) * 100) / 100,
    deviation_vs_imdb: withImdb.length
      ? Math.round(mean(withImdb.map((r) => r.YourRating - r.ImdbRating)) * 100) / 100 : 0,
    by_genre: groupAvg(rated, (r) => splitList(r.Genres), MIN_GENRE_N),
    by_director: groupAvg(rated, (r) => splitList(r.Directors), MIN_DIRECTOR_N).slice(0, TOP_DIRECTORS),
    top: sorted.slice(0, TOP_TITLES),
    bottom: sorted.slice(-TOP_TITLES).reverse(),
  };
}
