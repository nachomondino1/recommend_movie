// Arma lo que muestran Qué ver y Mi gusto a partir de los archivos del usuario, sus plataformas y el catálogo.
// Sin llamadas a APIs. Requiere catalog.js, taste.js y storage.js.

// Orden "recomendado": nota ponderada por votos (como el Top 250 de IMDb): rank = v/(v+m)·nota + m/(v+m)·C.
// m = votos a partir de los cuales la nota pesa más que el prior. La nota y los votos de TODO el catálogo son de TMDB
// (así son comparables entre sí); IMDb y TMDB tienen escalas de votos muy distintas, por eso m cambia según la fuente.
const PRIOR_RATING = 7.0, WEIGHT_VOTES_TMDB = 1000, WEIGHT_VOTES_IMDB = 25000;
const DIRECTOR_BOOST = 0.4;        // puntos que suma al orden recomendado un título de un director favorito
const FAV_GENRES = 3, FAV_DIRECTORS = 3;

const weightedRating = (rating, votes, m) => {
  const v = votes || 0;
  return (v / (v + m)) * rating + (m / (v + m)) * PRIOR_RATING;
};

const typeOf = (c) => (c.type === "movie" ? "Movie" : "TV Series");

// selected: Set de ids de plataforma.
// Devuelve { rows, taste, unavailable, stats }. rows incluye TODO el catálogo más lo que el usuario tiene fuera de él;
// cada fila trae onMine (está en sus plataformas), seen (ya la puntuó), inWatchlist y yourRating.
function buildProfile(data, selected) {
  const rated = data.ratings.filter((r) => r.YourRating != null)
    .map((r) => mergeRow(r, catalog.byImdb.get(r.Const)));
  const taste = buildTaste(rated);
  const favGenres = new Set(taste ? taste.by_genre.slice(0, FAV_GENRES).map((g) => g.label) : []);
  // Director favorito: al menos 2 títulos puntuados y promedio por encima de tu nota media
  const favDirectors = new Set(taste ? taste.by_director.filter((d) => d.avg > taste.mean_rating).slice(0, FAV_DIRECTORS).map((d) => d.label) : []);
  const favOf = (genres) => splitList(genres).filter((g) => favGenres.has(g));
  const favDirOf = (directors) => splitList(directors).filter((d) => favDirectors.has(d));

  const ratedByImdb = new Map(rated.map((r) => [r.Const, r]));
  const watchByImdb = new Map(data.watchlist.map((r) => [r.Const, r]));

  const finish = (row) => {
    row.fav = favOf(row.Genres);
    row.favDir = favDirOf(row.Directors);
    const m = row.ratingSource === "IMDb" ? WEIGHT_VOTES_IMDB : WEIGHT_VOTES_TMDB;
    row.rank = row.rating == null ? null
      : weightedRating(row.rating, row.votes, m) + (row.favDir.length ? DIRECTOR_BOOST : 0);
    row.searchText = normTitle(row.Title + " " + (row.altTitle || ""));
    return row;
  };

  const rows = [];

  // 1) Todo el catálogo
  for (const c of catalog.data.titles) {
    const w = c.imdb ? watchByImdb.get(c.imdb) : null;
    const rd = c.imdb ? ratedByImdb.get(c.imdb) : null;
    const csv = rd || w;                                        // lo que el usuario sabe de este título
    const seen = !!rd;
    const mine = c.providers.filter((id) => selected.has(id));
    rows.push(finish({
      Const: c.imdb || `tmdb:${c.type}:${c.id}`, Title: csv ? csv.Title : c.title, altTitle: csv ? c.title : "",
      Type: typeOf(c), Year: c.year,
      Genres: (csv && csv.Genres) || c.genres.join(", "),
      Directors: (csv && csv.Directors) || c.directors.join(", "),
      rating: c.rating, votes: c.votes, ratingSource: "TMDB",
      imdbRating: csv ? csv.ImdbRating : null, imdbVotes: csv ? csv.NumVotes : null,
      Runtime: c.runtime, poster_path: c.poster, overview: c.overview, seasons: c.seasons,
      providers: providerNames(c.providers), where: providerNames(mine),
      others: providerNames(c.providers.filter((id) => !selected.has(id))),
      onMine: mine.length > 0, inWatchlist: !!w && !rd, seen, yourRating: rd ? rd.YourRating : null,
      inCatalog: true,
      URL: c.imdb ? `https://www.imdb.com/title/${c.imdb}` : `https://www.themoviedb.org/${c.type}/${c.id}`,
    }));
  }

  // 2) Lo del usuario que no está en el catálogo (no está en ninguna plataforma de la región): solo aparece al buscar
  const inCatalog = (imdb) => catalog.byImdb.has(imdb);
  const extra = (r, rd) => finish({
    Const: r.Const, Title: r.Title, altTitle: "", Type: r.Type, Year: r.Year, Genres: r.Genres, Directors: r.Directors,
    rating: r.ImdbRating, votes: r.NumVotes, ratingSource: "IMDb", imdbRating: r.ImdbRating, imdbVotes: r.NumVotes,
    Runtime: r.Runtime, poster_path: null, overview: "", seasons: null, providers: [], where: [], others: [],
    onMine: false, inWatchlist: !rd, seen: !!rd, yourRating: rd ? rd.YourRating : null, inCatalog: false, URL: r.URL,
  });
  rated.filter((r) => !inCatalog(r.Const)).forEach((r) => rows.push(extra(r, r)));
  data.watchlist.filter((r) => !inCatalog(r.Const) && !ratedByImdb.has(r.Const)).forEach((r) => rows.push(extra(r, null)));

  const unavailable = rows.filter((r) => r.inWatchlist && !r.onMine).length;
  const inMine = rows.filter((r) => r.onMine);
  const stats = {
    total: catalog.data.titles.length,
    movies: catalog.data.titles.filter((t) => t.type === "movie").length,
    series: catalog.data.titles.filter((t) => t.type !== "movie").length,
    providers: catalog.data.providers.length,
    mine: inMine.length,
    mineNew: inMine.filter((r) => !r.seen).length,
  };
  return { rows, taste, unavailable, stats };
}
