// Página "Tu número": cargar datos, ver tu número (desvío contra IMDb) y predecir la nota de cualquier título, todo en una pantalla.
// Orden de la pantalla: carga de datos (plegada si ya hay datos) -> tu número y qué tan confiable es -> predecir -> gráficos.
// Requiere shared.js, csv.js, catalog.js, number.js y storage.js.

// ---- Carga de archivos de IMDb ----
function setMsg(text, isError) {
  $("uploadMsg").textContent = text;
  $("uploadMsg").className = "msg" + (isError ? " msg--error" : "");
}

async function ingest(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  $("uploadDone").hidden = true;
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
  data.savedAt = new Date().toISOString();
  if (!saveData(data)) {
    setMsg("No pude guardar tus datos en este navegador (¿ventana privada?).", true);
    return;
  }
  setMsg(notes.join(" "), notes.length > 0);
  showDone(data);
}

function wireUpload() {
  const zone = $("dropzone"), input = $("fileInput");
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => { ingest(input.files); input.value = ""; });
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("dropzone--over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("dropzone--over"); }));
  zone.addEventListener("drop", (e) => ingest(e.dataTransfer.files));
}



// Con los archivos ya guardados: se muestra el resultado y se baja hasta tu número (no hay recarga ni cambio de página).
async function showDone(data) {
  $("uploadDoneText").textContent = `Cargamos ${data.ratings.length} notas.`;
  renderHeader("numero");
  await showResults();
  const target = $("resultado");
  if (!target.closest("[hidden]")) target.scrollIntoView({ block: "start", behavior: reducedMotion() ? "auto" : "smooth" });
}

// ---- Tu número y sus gráficos ----
const pct = (x) => Math.round(x * 100) + " %";

function renderHero(r) {
  $("numBig").textContent = signed(r.mean);
  const abs = fmtNum(Math.abs(r.mean));
  $("numText").textContent = Math.abs(r.mean) < 0.3 ? "Puntuás casi igual que IMDb."
    : r.mean < 0 ? `Puntuás, en promedio, ${abs} puntos por debajo de IMDb.`
    : `Puntuás, en promedio, ${abs} puntos por encima de IMDb.`;
  const half = Math.abs(r.median) < 0.3 ? "" : r.median < 0
    ? ` La mitad de tus notas quedó al menos ${fmtNum(Math.abs(r.median))} por debajo de IMDb.`
    : ` La mitad de tus notas quedó al menos ${fmtNum(r.median)} por encima de IMDb.`;
  $("numNote").textContent = `Calculado con tus ${r.n} notas.${half}`;
  $("rMae").textContent = "±" + fmtNum(r.mae);
  $("rW1").textContent = pct(r.within1);
  $("rW2").textContent = pct(r.within2);
}

// Eje x: nota de IMDb; eje y: tu nota.
function renderScatter(r) {
  const W = 420, H = 320, m = { l: 34, r: 12, t: 12, b: 34 };
  const x = (v) => m.l + ((v - 1) / 9) * (W - m.l - m.r);
  const y = (v) => H - m.b - ((v - 1) / 9) * (H - m.t - m.b);
  const ticks = [2, 4, 6, 8, 10];
  const line = (off) => {
    const x1 = Math.max(1, 1 - off), x2 = Math.min(10, 10 - off);   // recorta la línea a la caja 1–10
    return `${x(x1).toFixed(1)},${y(x1 + off).toFixed(1)} ${x(x2).toFixed(1)},${y(x2 + off).toFixed(1)}`;
  };
  $("scatter").innerHTML = `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="Tu nota contra la nota de IMDb">
    ${ticks.map((t) => `<line x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}" class="grid"/>
      <text x="${m.l - 8}" y="${y(t) + 4}" class="tick" text-anchor="end">${t}</text>
      <text x="${x(t)}" y="${H - m.b + 18}" class="tick" text-anchor="middle">${t}</text>`).join("")}
    <polyline points="${line(0)}" class="ref-line"/>
    <polyline points="${line(r.mean)}" class="num-line"/>
    ${r.rows.map((p) => `<circle cx="${x(p.ImdbRating).toFixed(1)}" cy="${y(p.YourRating).toFixed(1)}" r="3.6" class="dot"><title>${esc(p.Title)}: vos ${p.YourRating}, IMDb ${p.ImdbRating}</title></circle>`).join("")}
    <text x="${(W + m.l) / 2}" y="${H - 4}" class="axis" text-anchor="middle">Nota de IMDb</text>
    <text x="12" y="${H / 2}" class="axis" text-anchor="middle" transform="rotate(-90 12 ${H / 2})">Tu nota</text>
  </svg>
  <div class="legend"><span><i class="lg lg--ref"></i>Igual que IMDb</span><span><i class="lg lg--num"></i>IMDb ${signed(r.mean)} (tu número)</span></div>`;
}

// Desvíos redondeados al entero más cercano, de −6 a +4 (lo que cae afuera se agrupa en las puntas).
function renderHisto(r) {
  const lo = -6, hi = 4, counts = new Map();
  for (let k = lo; k <= hi; k++) counts.set(k, 0);
  r.rows.forEach((p) => { const k = Math.max(lo, Math.min(hi, Math.round(p.dev))); counts.set(k, counts.get(k) + 1); });
  const max = Math.max(...counts.values(), 1), meanBin = Math.round(r.mean);
  $("histo").innerHTML = `<div class="histo">${[...counts].map(([k, v]) => `
    <div class="histo-col${k === meanBin ? " histo-col--mean" : ""}" title="${v} títulos a ${signed(k, 0)} de IMDb">
      <span class="histo-n">${v || ""}</span>
      <span class="histo-bar" style="height:${(v / max) * 100}%"></span>
      <span class="histo-x">${k > 0 ? "+" + k : k === 0 ? "0" : "−" + Math.abs(k)}</span>
    </div>`).join("")}</div>
    <p class="note histo-cap">Desv&iacute;o: tu nota menos la de IMDb. La barra resaltada es la de tu n&uacute;mero.</p>`;
}

function renderGaps(r) {
  const row = (p) => `<li><a class="title-link" href="${esc(p.URL)}" target="_blank" rel="noopener">${esc(p.Title)}</a>
    <span class="item-meta">vos ${p.YourRating} · IMDb ${fmtNum(p.ImdbRating)}</span></li>`;
  const up = [...r.rows].filter((p) => p.dev > 0).sort((a, b) => b.dev - a.dev).slice(0, 4);
  const down = [...r.rows].filter((p) => p.dev < 0).sort((a, b) => a.dev - b.dev).slice(0, 4);
  $("gaps").innerHTML = `
    <div class="vs-label">Los defendés más que IMDb</div><ul class="vs-list">${up.map(row).join("")}</ul>
    <div class="vs-label">IMDb los quiere más que vos</div><ul class="vs-list">${down.map(row).join("")}</ul>`;
}


// ---- Predecir una nota ----
const MAX_RESULTS = 12, LOW_VOTES = 300;
let NUMBER = 0, ALL = [];

const votesLabel = (n) => n == null ? "" : n >= 1e6 ? fmtNum(n / 1e6) + " M votos" : n >= 1e5 ? fmtNum(n / 1000, 0) + " mil votos" : n >= 1000 ? fmtNum(n / 1000) + " mil votos" : n + " votos";

// Una fila unificada por título: lo que sabemos de tus archivos manda sobre lo del catálogo.
function buildRows(data) {
  const mine = new Map();
  data.ratings.forEach((r) => mine.set(r.Const, r));
  const rows = [], used = new Set();
  for (const c of catalog.data.titles) {
    const m = c.imdb ? mine.get(c.imdb) : null;
    if (m) used.add(c.imdb);
    const exact = m && m.ImdbRating != null;
    rows.push({
      key: c.imdb || `tmdb:${c.type}:${c.id}`, title: m ? m.Title : c.title, altTitle: m ? c.title : "",
      year: c.year, type: c.type === "movie" ? "Película" : "Serie", poster: c.poster,
      base: exact ? m.ImdbRating : c.rating, exact, votes: exact ? m.NumVotes : c.votes,
      seen: !!m, yourRating: m ? m.YourRating : null,
      url: c.imdb ? `https://www.imdb.com/title/${c.imdb}` : `https://www.themoviedb.org/${c.type}/${c.id}`,
    });
  }
  // Lo tuyo que no está en el catálogo (no está en ninguna plataforma): también se puede buscar y predecir
  for (const [id, m] of mine) {
    if (used.has(id) || m.ImdbRating == null) continue;
    rows.push({ key: id, title: m.Title, altTitle: "", year: m.Year, type: /movie/i.test(m.Type) ? "Película" : "Serie", poster: null,
      base: m.ImdbRating, exact: true, votes: m.NumVotes, seen: true, yourRating: m.YourRating, url: m.URL });
  }
  rows.forEach((r) => { r.pred = r.base != null ? predictRating(r.base, NUMBER) : null; r.search = normTitle(r.title + " " + r.altTitle); });
  return rows;
}

function rowHtml(r) {
  const lowVotes = r.votes != null && r.votes < LOW_VOTES;
  const img = r.poster ? `<img class="item-poster" src="${IMG}w154${r.poster}" alt="" loading="lazy" width="64" height="96">` : `<div class="item-poster"></div>`;
  const base = r.base == null ? "" : `${r.exact ? "IMDb" : "IMDb ≈"} ${fmtNum(r.base)}`;
  const note = r.seen ? `<span class="chip chip--seen">Ya la puntuaste: ${r.yourRating} · la predicción era ${fmtNum(r.pred)}</span>`
    : "";
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
  if (!tokens.length) return;
  const hits = ALL.filter((r) => tokens.every((t) => r.search.includes(t)))
    .sort((a, b) => (b.votes ?? 0) - (a.votes ?? 0));
  $("resultsTitle").textContent = hits.length ? `${hits.length > MAX_RESULTS ? `Los ${MAX_RESULTS} más votados de ${hits.length}` : hits.length + (hits.length === 1 ? " resultado" : " resultados")}` : "Sin resultados";
  $("resultsList").innerHTML = hits.length ? hits.slice(0, MAX_RESULTS).map(rowHtml).join("")
    : '<div class="empty-state">No encontré ese título. Probá con otro nombre.</div>';
}


// ---- Armado de la pantalla ----
let wired = false;

async function showResults() {
  const data = loadData();
  const loaded = data.ratings.length > 0;
  $("loadBox").open = !loaded;
  $("loadSummary").textContent = loaded ? "Actualizar mis datos" : "Cargá tus datos de IMDb";
  $("body").hidden = true;
  $("notEnough").hidden = true;
  if (!loaded) return;
  const r = computeNumber(data.ratings);
  if (!r.enough) {
    $("notEnough").hidden = false;
    $("notEnough").textContent = `Con ${r.n} notas todavía no alcanza para calcular un número confiable (hacen falta al menos ${MIN_RATINGS}).`;
    return;
  }
  $("body").hidden = false;
  renderHero(r);
  renderScatter(r);
  renderHisto(r);
  renderGaps(r);
  NUMBER = r.mean;
  try { await loadCatalog(); }
  catch (e) { $("method").textContent = e.message; return; }
  $("method").innerHTML = `Nota predicha = nota de IMDb ${signed(NUMBER)}, entre 1 y 10, con un error típico de ±${fmtNum(r.mae)} puntos. ` +
    `Para los títulos que no están en tus archivos usamos la nota de TMDB, que en 188 títulos medidos se parece a la de IMDb ` +
    `(diferencia media de 0,3 puntos); se marcan con ≈. Es una estimación simple: ningún modelo más complejo la mejoró con evidencia suficiente.`;
  ALL = buildRows(data);
  renderSearch($("q").value);
  if (!wired) {
    wired = true;
    let timer;
    $("q").addEventListener("input", (e) => { clearTimeout(timer); timer = setTimeout(() => renderSearch(e.target.value), 120); });
  }
}

renderSite("numero");
wireUpload();
showResults();
