// Página "Mi perfil": estadística descriptiva de tus notas (sin predicción).
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
