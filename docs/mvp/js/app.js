// Orquestación: catálogo + plataformas + archivos de IMDb -> afinidad -> UI. Sin llamadas a APIs.

let currentTaste = null;
const selected = new Set(loadPlatforms().map((p) => p.id));

function show(screen) {
  $("screen-onboarding").hidden = screen !== "onboarding";
  $("screen-app").hidden = screen !== "app";
  $("tabs").hidden = screen !== "app";
  $("btnSettings").hidden = screen !== "app";
}

function setMsg(text, isError) {
  $("uploadMsg").textContent = text;
  $("uploadMsg").className = "msg" + (isError ? " msg--error" : "");
}

function persistPlatforms() {
  savePlatforms(catalog.data.providers.filter((p) => selected.has(p.id)).map((p) => ({ id: p.id, name: p.name })));
}

const typeOf = (c) => (c.type === "movie" ? "Movie" : "TV Series");

function buildDashboard(data) {
  const rated = data.ratings.filter((r) => r.YourRating != null)
    .map((r) => mergeRow(r, catalog.byImdb.get(r.Const)));
  currentTaste = buildTaste(rated);
  const scorer = buildScorer(rated, currentTaste ? currentTaste.deviation_vs_imdb : 0);
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
    const s = scorer(m);
    watch.push({ ...m, score: s.score, why: s.why, inWatchlist: true });
  });

  // 2) Títulos nuevos del catálogo en tus plataformas
  const discovered = catalog.data.titles
    .filter((c) => c.providers.some((id) => selected.has(id)))
    .filter((c) => !(c.imdb && seenImdb.has(c.imdb)) && !seenTitles.has(normTitle(c.title) + "|" + c.year))
    .map((c) => {
      const row = {
        Const: c.imdb || `tmdb:${c.type}:${c.id}`, Title: c.title, Type: typeOf(c), Year: c.year,
        Genres: c.genres.join(", "), Directors: c.directors.join(", "), ImdbRating: c.rating,
        Runtime: c.runtime, poster_path: c.poster, overview: c.overview, seasons: c.seasons,
        providers: providerNames(c.providers), where: providerNames(c.providers.filter((id) => selected.has(id))),
        inWatchlist: false, URL: c.imdb ? `https://www.imdb.com/title/${c.imdb}` : `https://www.themoviedb.org/${c.type}/${c.id}`,
      };
      const s = scorer(row);
      return { ...row, score: s.score, why: s.why };
    })
    .filter((r) => r.score != null && (r.ImdbRating || 0) >= 6)
    .sort((a, b) => b.score - a.score)
    .slice(0, 60);

  const rows = [...watch, ...discovered];
  $("hoyEmpty").hidden = rows.length > 0;
  $("hoyBody").hidden = rows.length === 0;
  $("subtitle").textContent = (unavailable
    ? `${unavailable} títulos de tu watchlist no están en tus plataformas. ` : "") +
    `Catálogo actualizado el ${catalog.data.generated}.`;
  initList(rows);
  renderTaste(currentTaste);
  show("app");
}

async function ingest(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  if (!selected.size) { setMsg("Primero elegí al menos una plataforma (paso 1).", true); return; }
  persistPlatforms();
  setMsg("Leyendo archivos…");
  const results = await readImdbFiles(files);
  const data = loadData();
  const notes = [];
  for (const r of results) {
    if (!r.kind || !r.rows.length) notes.push(`"${r.name}" no parece un archivo de IMDb.`);
    else data[r.kind] = r.rows;
  }
  if (!data.ratings.length) {
    setMsg(notes.concat("Falta el archivo de tus notas (ratings.csv).").join(" "), true);
    return;
  }
  if (!saveData(data)) notes.push("No pude guardar tus datos en este navegador (¿ventana privada?).");
  setMsg(notes.join(" "), notes.length > 0);
  buildDashboard(data);
}

function updateContinue() {
  $("btnContinue").hidden = !loadData().ratings.length;
  $("btnContinue").disabled = !selected.size;
}

function initOnboarding() {
  renderProviders(catalog.data.providers, selected, (id) => {
    selected.has(id) ? selected.delete(id) : selected.add(id);
    persistPlatforms();
    updateContinue();
  });
  updateContinue();
}

function wireOnboarding() {
  const zone = $("dropzone"), input = $("fileInput");
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => { ingest(input.files); input.value = ""; });
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("dropzone--over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("dropzone--over"); }));
  zone.addEventListener("drop", (e) => ingest(e.dataTransfer.files));
  $("btnContinue").addEventListener("click", () => { persistPlatforms(); buildDashboard(loadData()); });
  $("btnSettings").addEventListener("click", () => { setMsg(""); updateContinue(); show("onboarding"); });
  $("btnClear").addEventListener("click", () => {
    if (!confirm("¿Borrar tus datos de este navegador?")) return;
    clearAllData();
    location.reload();
  });
}

function wireApp() {
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
  document.querySelectorAll(".tab-btn").forEach((btn) => btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
    $("panel-hoy").hidden = btn.dataset.tab !== "hoy";
    $("panel-analisis").hidden = btn.dataset.tab !== "analisis";
  }));
}

async function main() {
  wireOnboarding();
  wireApp();
  show("onboarding");
  try {
    await loadCatalog();
  } catch (e) {
    $("providers").innerHTML = `<div class="msg msg--error">${esc(e.message)}</div>`;
    return;
  }
  initOnboarding();
  const data = loadData();
  if (data.ratings.length && selected.size) buildDashboard(data);
}

main();
