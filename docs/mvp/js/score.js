// Afinidad de un título con el gusto del usuario (reglas, sin modelo entrenado).

const W_AFFINITY = 0.6, W_IMDB = 0.4, AFF_GENRE_MIN_N = 3, AFF_DIRECTOR_MIN_N = 1;

function avgMap(rated, keysOf) {
  const acc = new Map();
  for (const r of rated) for (const k of keysOf(r)) {
    const a = acc.get(k) || { n: 0, sum: 0 };
    a.n++; a.sum += r.YourRating; acc.set(k, a);
  }
  return acc;
}

function clamp(v) { return Math.max(1, Math.min(10, v)); }

// Devuelve score(row) -> { score, why: [géneros que explican la afinidad] }
function buildScorer(rated, deviation) {
  const genres = avgMap(rated, (r) => splitList(r.Genres));
  const directors = avgMap(rated, (r) => splitList(r.Directors));
  const avgOf = (keys, map, minN) => keys
    .map((k) => ({ k, a: map.get(k) }))
    .filter((x) => x.a && x.a.n >= minN)
    .map((x) => ({ k: x.k, avg: x.a.sum / x.a.n }));
  return function score(row) {
    if (row.ImdbRating == null) return { score: null, why: [] };
    const g = avgOf(splitList(row.Genres), genres, AFF_GENRE_MIN_N);
    const d = avgOf(splitList(row.Directors), directors, AFF_DIRECTOR_MIN_N);
    const sig = [g, d].filter((x) => x.length).map((x) => mean(x.map((y) => y.avg)));
    if (!sig.length) return { score: clamp(row.ImdbRating + deviation), why: [] };
    const why = g.sort((a, b) => b.avg - a.avg).slice(0, 2).map((x) => x.k);
    return { score: clamp(W_AFFINITY * mean(sig) + W_IMDB * row.ImdbRating), why };
  };
}
