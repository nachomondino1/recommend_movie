// Arma lo que muestran Qué ver y Mi gusto a partir de los archivos del usuario, sus plataformas y el catálogo.
// Sin llamadas a APIs. Requiere catalog.js, taste.js y storage.js.

// Orden: nota ponderada por votos (como el Top 250 de IMDb): rank = v/(v+m)·nota + m/(v+m)·C.
// m = votos a partir de los cuales la nota pesa más que el prior; IMDb y TMDB tienen escalas muy distintas.
const PRIOR_RATING = 7.0, WEIGHT_VOTES_IMDB = 25000, WEIGHT_VOTES_TMDB = 1000;
const MIN_VOTES_SUGGESTED = 500;  // evita sugerir títulos con nota alta pero casi sin votos

const weightedRating = (rating, votes, m) => {
  const v = votes || 0;
  return (v / (v + m)) * rating + (m / (v + m)) * PRIOR_RATING;
};

const typeOf = (c) => (c.type === "movie" ? "Movie" : "TV Series");

// selected: Set de ids de plataforma. Devuelve { rows, taste, unavailable }.
function buildProfile(data, selected) {
  const rated = data.ratings.filter((r) => r.YourRating != null)
    .map((r) => mergeRow(r, catalog.byImdb.get(r.Const)));
  const taste = buildTaste(rated);
  const favGenres = new Set(taste ? taste.by_genre.slice(0, 3).map((g) => g.label) : []);
  const favOf = (genres) => splitList(genres).filter((g) => favGenres.has(g));
  const ratedIds = new Set(rated.map((r) => r.Const));
  const seenImdb = new Set([...ratedIds, ...data.watchlist.map((r) => r.Const)]);
  const seenTitles = new Set([...rated, ...data.watchlist].map((r) => normTitle(r.Title) + "|" + r.Year));

  // 1) Tu watchlist, solo lo disponible en tus plataformas
  const watch = [];
  let unavailable = 0;
  data.watchlist.filter((r) => !ratedIds.has(r.Const)).forEach((r) => {
    const cat = catalog.byImdb.get(r.Const);
    const m = mergeRow(r, cat);
    m.where = cat ? providerNames(cat.providers.filter((id) => selected.has(id))) : [];
    if (!m.where.length) { unavailable++; return; }
    watch.push({ ...m, fav: favOf(m.Genres), inWatchlist: true,
      rank: m.ImdbRating == null ? null : weightedRating(m.ImdbRating, m.NumVotes, WEIGHT_VOTES_IMDB) });
  });

  // 2) Títulos nuevos del catálogo en tus plataformas
  const discovered = catalog.data.titles
    .filter((c) => c.providers.some((id) => selected.has(id)))
    .filter((c) => (c.votes || 0) >= MIN_VOTES_SUGGESTED)
    .filter((c) => !(c.imdb && seenImdb.has(c.imdb)) && !seenTitles.has(normTitle(c.title) + "|" + c.year))
    .map((c) => {
      const row = {
        Const: c.imdb || `tmdb:${c.type}:${c.id}`, Title: c.title, Type: typeOf(c), Year: c.year,
        Genres: c.genres.join(", "), Directors: c.directors.join(", "), ImdbRating: c.rating, NumVotes: c.votes,
        Runtime: c.runtime, poster_path: c.poster, overview: c.overview, seasons: c.seasons,
        providers: providerNames(c.providers), where: providerNames(c.providers.filter((id) => selected.has(id))),
        inWatchlist: false, URL: c.imdb ? `https://www.imdb.com/title/${c.imdb}` : `https://www.themoviedb.org/${c.type}/${c.id}`,
      };
      return { ...row, fav: favOf(row.Genres), rank: weightedRating(row.ImdbRating, row.NumVotes, WEIGHT_VOTES_TMDB) };
    })
    .filter((r) => (r.ImdbRating || 0) >= 6)
    .sort((a, b) => b.rank - a.rank)
    .slice(0, 60);

  return { rows: [...watch, ...discovered], taste, unavailable };
}
