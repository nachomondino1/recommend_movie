// Página "Qué ver": tu watchlist y títulos nuevos en tus plataformas, ordenados por nota ponderada por votos.
// Requiere shared.js, profile.js, catalog.js, taste.js y storage.js.

const PAGE_SIZE = 20;
const LOW_VOTES = 1000;  // por debajo de esto la nota no es confiable
const state = { rows: [], current: [], shown: PAGE_SIZE, type: "", genre: "", onlyWatchlist: false };

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

const whereChips = (r) => (r.where || []).map((p) => `<span class="chip">${esc(p)}</span>`).join("");

function whyLine(r) {
  if (!r.fav || !r.fav.length) return "";
  return `<div class="item-why">De tus géneros favoritos: ${r.fav.map((g) => esc(genreEs(g))).join(" y ")}</div>`;
}

function initList(rows) {
  state.rows = rows;
  const genres = [...new Set(rows.flatMap((r) => splitList(r.Genres)))].sort();
  $("fGenre").innerHTML = '<option value="">Todos los géneros</option>' +
    genres.map((g) => `<option value="${esc(g)}">${esc(genreEs(g))}</option>`).join("");
  renderList();
}

function renderList() {
  let rows = state.rows.filter((r) => r.rank != null);
  if (state.type) rows = rows.filter((r) => (state.type === "Movie") === (r.Type === "Movie"));
  if (state.genre) rows = rows.filter((r) => splitList(r.Genres).includes(state.genre));
  if (state.onlyWatchlist) rows = rows.filter((r) => r.inWatchlist);
  rows.sort((a, b) => b.rank - a.rank);
  state.current = rows;

  const visible = rows.slice(0, state.shown);
  $("list").innerHTML = visible.length ? visible.map((r) => `
    <article class="item" data-key="${esc(r.Const)}">
      ${poster(r, "w154", "item-poster")}
      <div class="item-body">
        <button type="button" class="item-title" data-key="${esc(r.Const)}">${esc(r.Title)}</button>
        <div class="item-meta">${metaLine(r)}</div>
        ${whyLine(r)}
        <div class="item-where">${r.inWatchlist ? '<span class="chip chip--accent">En tu watchlist</span>' : ""}${whereChips(r)}</div>
      </div>
      <div class="item-score" title="Nota y votos en ${r.inWatchlist ? "IMDb" : "TMDB (menos votantes que IMDb)"}">
        <span class="pill" style="background:${colorFor(r.ImdbRating)}">${r.ImdbRating.toFixed(1)}</span>
        <span class="item-score-l">nota</span>
        <span class="item-votes${r.NumVotes != null && r.NumVotes < LOW_VOTES ? " item-votes--low" : ""}">${votesLabel(r.NumVotes)}</span>
      </div>
    </article>`).join("")
    : '<div class="empty-state">No hay títulos con estos filtros.</div>';
  $("btnMore").hidden = rows.length <= state.shown;
  $("resultCount").textContent = rows.length ? `Mostrando ${visible.length} de ${rows.length}` : "";
}

function pickForMe() {
  const rows = state.current.slice(0, 40);
  if (!rows.length) return;
  const w = rows.map((r) => Math.max(0.01, r.rank) ** 2);
  let x = Math.random() * w.reduce((a, b) => a + b, 0);
  for (let i = 0; i < rows.length; i++) { x -= w[i]; if (x <= 0) return openModal(rows[i].Const, true); }
  openModal(rows[rows.length - 1].Const, true);
}

function openModal(key, fromPick) {
  const r = state.rows.find((d) => d.Const === key);
  if (!r) return;
  $("modalBody").innerHTML = `
    <div class="modal-head">
      ${poster(r, "w185", "modal-poster")}
      <div>
        <h3>${esc(r.Title)}</h3>
        <div class="item-meta">${metaLine(r)}</div>
        ${whyLine(r)}
        <div class="item-where">${r.inWatchlist ? '<span class="chip chip--accent">En tu watchlist</span>' : ""}${whereChips(r)}</div>
      </div>
    </div>
    <p class="modal-text">${esc(r.overview) || "Sin sinopsis."}</p>
    <div class="modal-actions">
      ${fromPick ? '<button type="button" class="btn" id="btnAnother">Elegir otra</button>' : ""}
      <a class="btn btn--ghost" href="${esc(r.URL)}" target="_blank" rel="noopener">Ver ficha &#8599;</a>
    </div>`;
  const again = $("btnAnother");
  if (again) again.addEventListener("click", pickForMe);
  $("modalOverlay").hidden = false;
}

function wire() {
  document.querySelectorAll("#fType .seg-btn").forEach((b) => b.addEventListener("click", () => {
    state.type = b.dataset.type; state.shown = PAGE_SIZE;
    document.querySelectorAll("#fType .seg-btn").forEach((x) => x.classList.toggle("active", x === b));
    renderList();
  }));
  $("fGenre").addEventListener("change", (e) => { state.genre = e.target.value; state.shown = PAGE_SIZE; renderList(); });
  $("fWatchlist").addEventListener("change", (e) => { state.onlyWatchlist = e.target.checked; state.shown = PAGE_SIZE; renderList(); });
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
  const { rows, unavailable } = buildProfile(data, selected);
  $("hoyEmpty").hidden = rows.length > 0;
  $("hoyBody").hidden = rows.length === 0;
  $("subtitle").textContent = (unavailable
    ? `${unavailable} títulos de tu watchlist no están en tus plataformas. ` : "") +
    `Catálogo actualizado el ${catalog.data.generated}.`;
  initList(rows);
}

main();
