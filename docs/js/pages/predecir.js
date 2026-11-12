// Página "Predecir": nota predicha = nota de IMDb + tu número, para cualquier título del catálogo o de tus archivos.
// La nota de IMDb sale de tus archivos si el título está ahí (exacta); si no, se usa la de TMDB (~igual, ver el texto de método).
// Requiere shared.js, catalog.js, number.js y storage.js.

const PAGE_SIZE = 12, MAX_RESULTS = 12, LOW_VOTES = 300;
let NUMBER = 0, ALL = [], WATCH = [], shown = PAGE_SIZE;

const votesLabel = (n) => n == null ? "" : n >= 1e6 ? fmtNum(n / 1e6) + " M votos" : n >= 1e5 ? fmtNum(n / 1000, 0) + " mil votos" : n >= 1000 ? fmtNum(n / 1000) + " mil votos" : n + " votos";

// Una fila unificada por título: lo que sabemos de tus archivos manda sobre lo del catálogo.
function buildRows(data) {
  const mine = new Map();
  data.ratings.forEach((r) => mine.set(r.Const, { ...r, seen: true }));
  data.watchlist.forEach((r) => { if (!mine.has(r.Const)) mine.set(r.Const, { ...r, seen: false }); });
  const rows = [], used = new Set();
  for (const c of catalog.data.titles) {
    const m = c.imdb ? mine.get(c.imdb) : null;
    if (m) used.add(c.imdb);
    const exact = m && m.ImdbRating != null;
    rows.push({
      key: c.imdb || `tmdb:${c.type}:${c.id}`, title: m ? m.Title : c.title, altTitle: m ? c.title : "",
      year: c.year, type: c.type === "movie" ? "Película" : "Serie", poster: c.poster,
      base: exact ? m.ImdbRating : c.rating, exact, votes: exact ? m.NumVotes : c.votes,
      seen: !!m && m.seen, yourRating: m && m.seen ? m.YourRating : null, inWatchlist: !!m && !m.seen,
      url: c.imdb ? `https://www.imdb.com/title/${c.imdb}` : `https://www.themoviedb.org/${c.type}/${c.id}`,
    });
  }
  // Lo tuyo que no está en el catálogo (no está en ninguna plataforma): también se puede buscar y predecir
  for (const [id, m] of mine) {
    if (used.has(id) || m.ImdbRating == null) continue;
    rows.push({ key: id, title: m.Title, altTitle: "", year: m.Year, type: /movie/i.test(m.Type) ? "Película" : "Serie", poster: null,
      base: m.ImdbRating, exact: true, votes: m.NumVotes, seen: m.seen, yourRating: m.seen ? m.YourRating : null, inWatchlist: !m.seen, url: m.URL });
  }
  rows.forEach((r) => { r.pred = r.base != null ? predictRating(r.base, NUMBER) : null; r.search = normTitle(r.title + " " + r.altTitle); });
  return rows;
}

function rowHtml(r) {
  const lowVotes = r.votes != null && r.votes < LOW_VOTES;
  const img = r.poster ? `<img class="item-poster" src="${IMG}w154${r.poster}" alt="" loading="lazy" width="64" height="96">` : `<div class="item-poster"></div>`;
  const base = r.base == null ? "" : `${r.exact ? "IMDb" : "IMDb ≈"} ${fmtNum(r.base)}`;
  const note = r.seen ? `<span class="chip chip--seen">Ya la puntuaste: ${r.yourRating} · la predicción era ${fmtNum(r.pred)}</span>`
    : r.inWatchlist ? `<span class="chip chip--accent">En tu watchlist</span>` : "";
  return `<article class="pred">
    ${img}
    <div class="pred-body">
      <a class="title-link" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>
      <div class="item-meta">${[r.year, r.type].filter(Boolean).map(esc).join(" · ")}</div>
      <div class="item-meta">${base}${r.votes != null ? " · " + votesLabel(r.votes) : ""}</div>
      <div class="item-where">${note}${lowVotes && !r.exact ? '<span class="chip chip--muted">pocos votos: nota poco confiable</span>' : ""}</div>
    </div>
    ${r.pred == null ? "" : `<div class="pred-score"><span class="pill" style="background:${colorFor(r.pred)}">${fmtNum(r.pred)}</span><span class="item-score-l">tu nota predicha</span></div>`}
  </article>`;
}

function renderSearch(q) {
  const tokens = normTitle(q).split(" ").filter(Boolean);
  $("results").hidden = !tokens.length;
  $("watchSection").hidden = tokens.length > 0 || !WATCH.length;
  if (!tokens.length) return;
  const hits = ALL.filter((r) => tokens.every((t) => r.search.includes(t)))
    .sort((a, b) => (b.votes ?? 0) - (a.votes ?? 0));
  $("resultsTitle").textContent = hits.length ? `${hits.length > MAX_RESULTS ? `Los ${MAX_RESULTS} más votados de ${hits.length}` : hits.length + (hits.length === 1 ? " resultado" : " resultados")}` : "Sin resultados";
  $("resultsList").innerHTML = hits.length ? hits.slice(0, MAX_RESULTS).map(rowHtml).join("")
    : '<div class="empty-state">No encontré ese título. Probá con otro nombre.</div>';
}

function renderWatch() {
  $("watchList").innerHTML = WATCH.slice(0, shown).map(rowHtml).join("");
  $("btnMore").hidden = shown >= WATCH.length;
}

async function main() {
  renderSite("predecir");
  const data = loadData();
  if (!data.ratings.length) { $("noData").hidden = false; return; }
  const r = computeNumber(data.ratings);
  if (!r.enough) {
    $("notEnough").hidden = false;
    $("notEnough").textContent = `Con ${r.n} notas todavía no alcanza para calcular tu número (hacen falta al menos ${MIN_RATINGS}).`;
    return;
  }
  try { await loadCatalog(); }
  catch (e) { $("notEnough").hidden = false; $("notEnough").textContent = e.message; return; }
  NUMBER = r.mean;
  $("myNumber").textContent = signed(NUMBER);
  $("body").hidden = false;
  $("method").innerHTML = `Nota predicha = nota de IMDb ${signed(NUMBER)}, entre 1 y 10, con un error típico de ±${fmtNum(r.mae)} puntos. ` +
    `Para los títulos que no están en tus archivos usamos la nota de TMDB, que en 188 títulos medidos se parece a la de IMDb ` +
    `(diferencia media de 0,3 puntos); se marcan con ≈. Es una estimación simple: ningún modelo más complejo la mejoró con evidencia suficiente.`;
  ALL = buildRows(data);
  WATCH = ALL.filter((x) => x.inWatchlist && x.pred != null).sort((a, b) => b.pred - a.pred || (b.votes ?? 0) - (a.votes ?? 0));
  renderWatch();
  renderSearch("");
  let timer;
  $("q").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => renderSearch(e.target.value), 120); });
  $("btnMore").addEventListener("click", () => { shown += PAGE_SIZE; renderWatch(); });
}

main();
