// Página "Mis puntuaciones": estadística descriptiva de tus notas (sin predicción).
// Requiere shared.js, profile.js, catalog.js, taste.js y storage.js.

// Cada fila se despliega y muestra los títulos que se tuvieron en cuenta (con tu nota).
function hbarList(id, items, labelOf = (l) => l) {
  $(id).innerHTML = items.length ? items.map((it) => `
    <details class="hbar-item">
      <summary class="hbar">
        <span class="hbar-label" title="${esc(labelOf(it.label))}">${esc(labelOf(it.label))}</span>
        <span class="hbar-track"><span class="hbar-fill" style="width:${it.avg * 10}%;background:${colorFor(it.avg)}"></span></span>
        <span class="hbar-value">${it.avg.toFixed(1)} · ${it.n}</span>
        <span class="chev" aria-hidden="true">&#9662;</span>
      </summary>
      <ul class="hbar-titles">${it.titles.map((t) => `
        <li>
          <a class="title-link" href="${esc(t.URL)}" target="_blank" rel="noopener">${esc(t.Title)}</a>
          <span class="item-meta">${t.Year ?? ""}</span>
          <span class="pill pill--sm" style="background:${colorFor(t.YourRating)}" title="Tu nota">${t.YourRating}</span>
        </li>`).join("")}
      </ul>
    </details>`).join("") : '<div class="empty-note">Todavía no hay suficientes títulos.</div>';
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

// ---- Estadísticas extra: salen directo de los archivos del usuario (nota propia, nota de IMDb, duración, año) ----
const avgOf = (a) => a.reduce((x, y) => x + y.YourRating, 0) / a.length;

// Filas de barras simples (sin desplegar): label, barra proporcional a la nota, promedio · cantidad
function barRows(id, groups, emptyMsg) {
  $(id).innerHTML = groups.length ? groups.map((g) => `
    <div class="hbar">
      <span class="hbar-label">${esc(g.label)}</span>
      <span class="hbar-track"><span class="hbar-fill" style="width:${g.avg * 10}%;background:${colorFor(g.avg)}"></span></span>
      <span class="hbar-value">${g.avg.toFixed(1)} · ${g.n}</span>
    </div>`).join("") : `<div class="empty-note">${emptyMsg}</div>`;
}

function renderHistogram(rated) {
  const you = Array(10).fill(0), imdb = Array(10).fill(0);
  rated.forEach((r) => {
    you[Math.min(10, Math.max(1, Math.round(r.YourRating))) - 1]++;
    if (r.ImdbRating != null) imdb[Math.min(10, Math.max(1, Math.round(r.ImdbRating))) - 1]++;
  });
  // La marca de IMDb se escala al mismo total de títulos que puntuó el usuario
  const nImdb = imdb.reduce((a, b) => a + b, 0) || 1;
  const scaled = imdb.map((v) => (v / nImdb) * rated.length);
  const max = Math.max(...you, ...scaled, 1);
  $("histo").innerHTML = `<div class="histo-legend"><span><i class="lg lg--you"></i>Tus notas</span><span><i class="lg lg--ref"></i>Si puntuaras como IMDb</span></div><div class="histo">${you.map((v, i) => `
    <div class="histo-col" title="Nota ${i + 1}: ${v} títulos">
      <span class="histo-n">${v || ""}</span>
      <span class="histo-bar" style="height:${(v / max) * 100}%"></span>
      <span class="histo-ref" style="bottom:${(scaled[i] / max) * 100}%"></span>
      <span class="histo-x">${i + 1}</span>
    </div>`).join("")}</div>`;
}

function renderRuntime(rated) {
  const movies = rated.filter((r) => r.Type === "Movie" && r.Runtime);
  const buckets = [["Hasta 90 min", 0, 90], ["90 a 120 min", 90, 120], ["120 a 150 min", 120, 150], ["Más de 150 min", 150, 1e9]];
  barRows("byRuntime", buckets.map(([label, lo, hi]) => {
    const g = movies.filter((r) => r.Runtime > lo && r.Runtime <= hi);
    return { label, n: g.length, avg: g.length ? avgOf(g) : 0 };
  }).filter((g) => g.n > 0), "Todavía no hay suficientes películas.");
  const mins = movies.reduce((a, r) => a + r.Runtime, 0);
  $("tHours").textContent = Math.round(mins / 60);
}

function renderDecades(rated) {
  const by = new Map();
  rated.filter((r) => r.Year).forEach((r) => {
    const d = Math.floor(r.Year / 10) * 10;
    (by.get(d) || by.set(d, []).get(d)).push(r);
  });
  barRows("byDecade", [...by.entries()].filter(([, g]) => g.length >= 3).sort((a, b) => b[0] - a[0])
    .map(([d, g]) => ({ label: `${d}s`, n: g.length, avg: avgOf(g) })), "Todavía no hay suficientes títulos.");
}

function renderVsImdb(rated) {
  const withBoth = rated.filter((r) => r.ImdbRating != null).map((r) => ({ ...r, diff: r.YourRating - r.ImdbRating }));
  const row = (r) => `
    <li><a class="title-link" href="${esc(r.URL)}" target="_blank" rel="noopener">${esc(r.Title)}</a>
      <span class="item-meta">vos ${r.YourRating} · IMDb ${r.ImdbRating.toFixed(1)}</span></li>`;
  const up = withBoth.filter((r) => r.diff > 0).sort((a, b) => b.diff - a.diff).slice(0, 4);
  const down = withBoth.filter((r) => r.diff < 0).sort((a, b) => a.diff - b.diff).slice(0, 4);
  $("vsImdb").innerHTML = `
    <div class="vs-label">Los defendés más que IMDb</div><ul class="vs-list">${up.map(row).join("")}</ul>
    <div class="vs-label">IMDb los quiere más que vos</div><ul class="vs-list">${down.map(row).join("")}</ul>`;
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
  const rated = loadData().ratings.filter((r) => r.YourRating != null);
  renderHistogram(rated);
  renderRuntime(rated);
  renderDecades(rated);
  renderVsImdb(rated);
  hbarList("rankGenre", t.by_genre.slice(0, 8), genreEs);
  hbarList("rankDirector", t.by_director);
  titleList("topList", t.top);
  titleList("bottomList", t.bottom);
}

async function main() {
  renderSite("mi-gusto");
  const data = loadData();
  if (!data.ratings.length) { $("noData").hidden = false; return; }
  try {
    await loadCatalog();
  } catch (e) {
    $("noData").hidden = false;
    $("noData").textContent = e.message;
    return;
  }
  renderTaste(buildProfile(data, new Set()).taste);
}

main();
