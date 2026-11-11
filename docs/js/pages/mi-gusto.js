// Página "Mi gusto": estadística descriptiva de tus notas (sin predicción).
// Requiere shared.js, profile.js, catalog.js, taste.js y storage.js.

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
  renderTaste(buildProfile(data, new Set(loadPlatforms().map((p) => p.id))).taste);
}

main();
