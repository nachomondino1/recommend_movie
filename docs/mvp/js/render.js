// UI: lista "Qué ver" (cards simples), elección de plataformas y "Mi gusto".

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const IMG = "https://image.tmdb.org/t/p/";
const PAGE_SIZE = 20;

const GENRE_ES = {
  Action: "Acción", Adventure: "Aventura", Animation: "Animación", Biography: "Biografía",
  Comedy: "Comedia", Crime: "Crimen", Documentary: "Documental", Drama: "Drama", Family: "Familia",
  Fantasy: "Fantasía", History: "Historia", Horror: "Terror", Music: "Música", Musical: "Musical",
  Mystery: "Misterio", Romance: "Romance", "Sci-Fi": "Ciencia ficción", Sport: "Deportes",
  Thriller: "Suspenso", War: "Bélica", Western: "Western", "Reality-TV": "Reality",
};
const genreEs = (g) => GENRE_ES[g] || g;

const state = { rows: [], current: [], shown: PAGE_SIZE, type: "", genre: "", onlyWatchlist: false };

function colorFor(v) {
  const t = Math.max(0, Math.min(1, (v - 3) / 5));
  return `hsl(${t * 120}, 56%, 36%)`;
}

const typeLabel = (r) => (r.Type === "Movie" ? "Película" : "Serie");

function metaLine(r) {
  const parts = [r.Year, typeLabel(r), r.ImdbRating != null ? "Nota " + r.ImdbRating : null];
  if (r.seasons && r.Type !== "Movie") parts.push(r.seasons + (r.seasons === 1 ? " temporada" : " temporadas"));
  else if (r.Runtime) parts.push(Math.round(r.Runtime) + " min");
  return parts.filter(Boolean).map(esc).join(" · ");
}

function poster(r, size, cls) {
  return r.poster_path
    ? `<img class="${cls}" src="${IMG}${size}${r.poster_path}" alt="" loading="lazy">`
    : `<div class="${cls}"></div>`;
}

function whereChips(r) {
  return r.where && r.where.length
    ? r.where.map((p) => `<span class="chip">${esc(p)}</span>`).join("")
    : "";
}

function whyLine(r) {
  if (!r.why || !r.why.length) return "";
  return `<div class="item-why">Te puede gustar: ${r.why.map((g) => esc(genreEs(g))).join(" y ")}</div>`;
}

// ---- plataformas (onboarding) --------------------------------------------
function renderProviders(list, selected, onToggle) {
  $("providers").innerHTML = list.map((p) => `
    <button type="button" class="prov${selected.has(p.id) ? " prov--on" : ""}" data-id="${p.id}"
      aria-pressed="${selected.has(p.id)}">
      ${p.logo ? `<img src="${IMG}w92${p.logo}" alt="" loading="lazy">` : ""}
      <span>${esc(p.name)}</span>
    </button>`).join("");
  $("providers").querySelectorAll(".prov").forEach((b) => b.addEventListener("click", () => {
    onToggle(Number(b.dataset.id));
    b.classList.toggle("prov--on", selected.has(Number(b.dataset.id)));
    b.setAttribute("aria-pressed", selected.has(Number(b.dataset.id)));
  }));
}

// ---- Qué ver --------------------------------------------------------------
function initList(rows) {
  state.rows = rows;
  state.type = ""; state.genre = ""; state.onlyWatchlist = false; state.shown = PAGE_SIZE;
  const genres = [...new Set(rows.flatMap((r) => splitList(r.Genres)))].sort();
  $("fGenre").innerHTML = '<option value="">Todos los géneros</option>' +
    genres.map((g) => `<option value="${esc(g)}">${esc(genreEs(g))}</option>`).join("");
  $("fGenre").value = "";
  $("fWatchlist").checked = false;
  document.querySelectorAll("#fType .seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.type === ""));
  renderList();
}

function renderList() {
  let rows = state.rows.filter((r) => r.score != null);
  if (state.type) rows = rows.filter((r) => (state.type === "Movie") === (r.Type === "Movie"));
  if (state.genre) rows = rows.filter((r) => splitList(r.Genres).includes(state.genre));
  if (state.onlyWatchlist) rows = rows.filter((r) => r.inWatchlist);
  rows.sort((a, b) => b.score - a.score);
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
      <div class="item-score" title="Qué tanto encaja con tu gusto">
        <span class="pill" style="background:${colorFor(r.score)}">${r.score.toFixed(1)}</span>
        <span class="item-score-l">para vos</span>
      </div>
    </article>`).join("")
    : '<div class="empty-state">No hay títulos con estos filtros.</div>';
  $("btnMore").hidden = rows.length <= state.shown;
  $("resultCount").textContent = rows.length
    ? `Mostrando ${visible.length} de ${rows.length}` : "";
}

function pickForMe() {
  const rows = state.current.slice(0, 40);
  if (!rows.length) return;
  const w = rows.map((r) => Math.max(0.01, r.score) ** 2);
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

// ---- Mi gusto -------------------------------------------------------------
function hbarList(id, items) {
  $(id).innerHTML = items.length ? items.map((it) => `
    <div class="hbar">
      <div class="hbar-label" title="${esc(it.label)}">${esc(genreEs(it.label))}</div>
      <div class="hbar-track"><div class="hbar-fill" style="width:${it.avg * 10}%;background:${colorFor(it.avg)}"></div></div>
      <div class="hbar-value">${it.avg.toFixed(1)}</div>
    </div>`).join("") : '<div class="empty-note">Todavía no hay suficientes títulos.</div>';
}

function titleList(id, items) {
  $(id).innerHTML = items.map((it) => `
    <div class="toplist-row">
      ${poster(it, "w92", "poster")}
      <div class="toplist-info">
        <a class="title-link" href="${esc(it.URL)}" target="_blank" rel="noopener">${esc(it.Title)}</a>
        <div class="item-meta">${it.Year ?? ""}</div>
      </div>
      <span class="pill" style="background:${colorFor(it.YourRating)}">${it.YourRating}</span>
    </div>`).join("");
}

function renderTaste(t) {
  $("analysisBody").hidden = !t;
  $("analysisEmpty").hidden = !!t;
  if (!t) return;
  $("tNRated").textContent = t.n_rated;
  $("tMean").textContent = t.mean_rating;
  $("tDev").textContent = (t.deviation_vs_imdb > 0 ? "+" : "") + t.deviation_vs_imdb.toFixed(1);
  $("devText").textContent = t.deviation_vs_imdb <= -0.5 ? "Sos más exigente que el promedio de IMDb."
    : t.deviation_vs_imdb >= 0.5 ? "Sos más generoso que el promedio de IMDb."
    : "Puntuás parecido al promedio de IMDb.";
  hbarList("rankGenre", t.by_genre.slice(0, 8));
  hbarList("rankDirector", t.by_director);
  titleList("topList", t.top);
  titleList("bottomList", t.bottom);
}
