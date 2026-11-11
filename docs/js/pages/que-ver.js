// Página "Qué ver": todo el catálogo en tus plataformas (sin lo que ya viste), con orden y filtros a tu criterio
// y un buscador por nombre que mira el catálogo entero. Requiere shared.js, profile.js, catalog.js, taste.js y storage.js.

const PAGE_SIZE = 20;
const LOW_VOTES = { TMDB: 300, IMDb: 1000 };  // por debajo de esto la nota no es confiable (escalas distintas)
const fmt = (n) => Number(n).toLocaleString("es-AR");

const state = { rows: [], current: [], shown: PAGE_SIZE, type: "", genre: "", onlyWatchlist: false, q: "", sort: "recomendado", minVotes: 0 };

// "recomendado" = nota ponderada por votos + impulso de directores favoritos (rank, ver profile.js)
const SORTS = {
  recomendado: (a, b) => (b.rank ?? -1) - (a.rank ?? -1),
  nota: (a, b) => (b.rating ?? -1) - (a.rating ?? -1) || (b.votes ?? 0) - (a.votes ?? 0),
  votos: (a, b) => (b.votes ?? 0) - (a.votes ?? 0),
  nuevas: (a, b) => (b.Year ?? 0) - (a.Year ?? 0),
  az: (a, b) => a.Title.localeCompare(b.Title, "es"),
};

function votesLabel(n) {
  if (n == null) return "";
  if (n >= 1e6) return (Math.round(n / 1e5) / 10).toString().replace(".", ",") + " M votos";
  if (n >= 1000) return (Math.round(n / 100) / 10).toString().replace(".", ",") + " mil votos";
  return n + (n === 1 ? " voto" : " votos");
}

function metaLine(r) {
  const parts = [r.Year, typeLabel(r)];
  if (r.seasons && r.Type !== "Movie") parts.push(r.seasons + (r.seasons === 1 ? " temporada" : " temporadas"));
  else if (r.Runtime) parts.push(Math.round(r.Runtime) + " min");
  return parts.filter(Boolean).map(esc).join(" · ");
}

function imdbLine(r) {
  if (r.ratingSource === "IMDb" || r.imdbRating == null) return "";
  return `<div class="item-meta">IMDb ${r.imdbRating}${r.imdbVotes != null ? " · " + votesLabel(r.imdbVotes) : ""}</div>`;
}

function chipsFor(r) {
  const chips = [];
  if (r.seen) chips.push(`<span class="chip chip--seen">Ya la viste · tu nota ${r.yourRating}</span>`);
  if (r.inWatchlist) chips.push('<span class="chip chip--accent">En tu watchlist</span>');
  chips.push(...r.where.map((p) => `<span class="chip">${esc(p)}</span>`));
  if (!r.inCatalog) chips.push('<span class="chip chip--muted">No está en ninguna plataforma de la región</span>');
  else if (!r.onMine) chips.push('<span class="chip chip--muted">No está en tus plataformas</span>');
  return chips.join("");
}

function othersLine(r) {
  return !r.onMine && r.others.length ? `<div class="item-meta">Disponible en: ${r.others.map(esc).join(", ")}</div>` : "";
}

function whyLine(r) {
  const lines = [];
  if (r.favDir && r.favDir.length) lines.push(`De tus directores favoritos: ${r.favDir.map(esc).join(" y ")}`);
  if (r.fav && r.fav.length) lines.push(`De tus géneros favoritos: ${r.fav.map((g) => esc(genreEs(g))).join(" y ")}`);
  return lines.map((l) => `<div class="item-why">${l}</div>`).join("");
}

function scoreBlock(r) {
  if (r.rating == null) return "";
  const low = (r.votes ?? 0) < LOW_VOTES[r.ratingSource];
  return `
    <div class="item-score" title="Nota y votos en ${r.ratingSource}">
      <span class="pill" style="background:${colorFor(r.rating)}">${r.rating.toFixed(1)}</span>
      <span class="item-score-l">nota</span>
      <span class="item-votes${low ? " item-votes--low" : ""}">${votesLabel(r.votes)}</span>
    </div>`;
}

function initList(rows, stats) {
  state.rows = rows;
  const genres = [...new Set(rows.flatMap((r) => splitList(r.Genres)))].sort();
  $("fGenre").innerHTML = '<option value="">Todos los géneros</option>' +
    genres.map((g) => `<option value="${esc(g)}">${esc(genreEs(g))}</option>`).join("");
  renderList();
}

function currentRows() {
  const tokens = normTitle(state.q).split(" ").filter(Boolean);
  let rows;
  if (tokens.length) {
    // Buscando: se mira TODO (cualquier plataforma, también lo ya visto) y se ignoran los demás filtros
    rows = state.rows.filter((r) => tokens.every((t) => r.searchText.includes(t)));
  } else {
    rows = state.rows.filter((r) => r.onMine && !r.seen);
    if (state.type) rows = rows.filter((r) => (state.type === "Movie") === (r.Type === "Movie"));
    if (state.genre) rows = rows.filter((r) => splitList(r.Genres).includes(state.genre));
    if (state.onlyWatchlist) rows = rows.filter((r) => r.inWatchlist);
    if (state.minVotes) rows = rows.filter((r) => (r.votes ?? 0) >= state.minVotes);
  }
  return rows.sort(SORTS[state.sort]);
}

function renderList() {
  const searching = normTitle(state.q).length > 0;
  const rows = state.current = currentRows();
  const visible = rows.slice(0, state.shown);
  $("searchNote").hidden = !searching;
  $("list").innerHTML = visible.length ? visible.map((r) => `
    <article class="item" data-key="${esc(r.Const)}">
      ${poster(r, "w154", "item-poster")}
      <div class="item-body">
        <button type="button" class="item-title" data-key="${esc(r.Const)}">${esc(r.Title)}</button>
        <div class="item-meta">${metaLine(r)}</div>
        ${imdbLine(r)}
        ${whyLine(r)}
        <div class="item-where">${chipsFor(r)}</div>
        ${othersLine(r)}
      </div>
      ${scoreBlock(r)}
    </article>`).join("")
    : `<div class="empty-state">${searching ? "No encontramos ese título en el catálogo." : "No hay títulos con estos filtros."}</div>`;
  $("btnMore").hidden = rows.length <= state.shown;
  $("resultCount").textContent = rows.length ? `Mostrando ${fmt(visible.length)} de ${fmt(rows.length)}` : "";
}

function pickForMe() {
  const rows = state.current.filter((r) => r.rank != null && !r.seen).slice(0, 40);
  if (!rows.length) return;
  const w = rows.map((r) => Math.max(0.01, r.rank) ** 2);
  let x = Math.random() * w.reduce((a, b) => a + b, 0);
  for (let i = 0; i < rows.length; i++) { x -= w[i]; if (x <= 0) return openModal(rows[i].Const, true); }
  openModal(rows[rows.length - 1].Const, true);
}

// Los links externos se abren siempre en una pestaña nueva
const extLink = (href, inner, cls = "") =>
  `<a class="${cls}" href="${esc(href)}" target="_blank" rel="noopener noreferrer">${inner}</a>`;

function openModal(key, fromPick) {
  const r = state.rows.find((d) => d.Const === key);
  if (!r) return;
  const site = r.URL.includes("imdb.com") ? "IMDb" : "TMDB";
  $("modalBody").innerHTML = `
    <div class="modal-head">
      ${extLink(r.URL, poster(r, "w185", "modal-poster"), "modal-poster-link")}
      <div>
        <h3>${extLink(r.URL, esc(r.Title), "title-link")}</h3>
        <div class="item-meta">${metaLine(r)}</div>
        ${r.rating != null ? `<div class="item-meta">Nota ${r.rating.toFixed(1)} · ${votesLabel(r.votes)} (${r.ratingSource})</div>` : ""}
        ${imdbLine(r)}
        ${whyLine(r)}
        <div class="item-where">${chipsFor(r)}</div>
        ${othersLine(r)}
      </div>
    </div>
    <p class="modal-text">${esc(r.overview) || "Sin sinopsis."}</p>
    <div class="modal-actions">
      ${fromPick ? '<button type="button" class="btn" id="btnAnother">Elegir otra</button>' : ""}
      ${extLink(r.URL, `Ver en ${site} &#8599;`, "btn btn--ghost")}
    </div>`;
  const again = $("btnAnother");
  if (again) again.addEventListener("click", pickForMe);
  $("modalOverlay").hidden = false;
}

function resetAndRender() { state.shown = PAGE_SIZE; renderList(); }

function wire() {
  document.querySelectorAll("#fType .seg-btn").forEach((b) => b.addEventListener("click", () => {
    state.type = b.dataset.type;
    document.querySelectorAll("#fType .seg-btn").forEach((x) => x.classList.toggle("active", x === b));
    resetAndRender();
  }));
  $("fGenre").addEventListener("change", (e) => { state.genre = e.target.value; resetAndRender(); });
  $("fWatchlist").addEventListener("change", (e) => { state.onlyWatchlist = e.target.checked; resetAndRender(); });
  $("fSort").addEventListener("change", (e) => { state.sort = e.target.value; resetAndRender(); });
  $("fMinVotes").addEventListener("change", (e) => { state.minVotes = Number(e.target.value); resetAndRender(); });
  let timer;
  $("q").addEventListener("input", (e) => {
    clearTimeout(timer);
    timer = setTimeout(() => { state.q = e.target.value; resetAndRender(); }, 150);
  });
  $("btnMore").addEventListener("click", () => { state.shown += PAGE_SIZE; renderList(); });
  $("list").addEventListener("click", (e) => {
    const btn = e.target.closest(".item-title");
    if (btn) openModal(btn.dataset.key, false);
  });
  $("pickForMe").addEventListener("click", pickForMe);
  $("modalClose").addEventListener("click", () => ($("modalOverlay").hidden = true));
  $("modalOverlay").addEventListener("click", (e) => { if (e.target.id === "modalOverlay") $("modalOverlay").hidden = true; });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") $("modalOverlay").hidden = true; });
}

async function main() {
  renderSite("que-ver");
  wire();
  $("filtersBox").open = window.innerWidth > 640;  // en el celular arranca plegado para ver la lista enseguida
  const data = loadData();
  const selected = new Set(loadPlatforms().map((p) => p.id));
  if (!data.ratings.length || !selected.size) { $("noData").hidden = false; return; }
  try {
    await loadCatalog();
  } catch (e) {
    $("noData").hidden = false;
    $("noData").textContent = e.message;
    return;
  }
  const { rows, unavailable, stats } = buildProfile(data, selected);
  $("hoyEmpty").hidden = stats.mineNew > 0;
  $("hoyBody").hidden = false;
  $("subtitle").textContent = unavailable ? `${unavailable} títulos de tu watchlist no están en tus plataformas.` : "";
  initList(rows, stats);
}

main();
