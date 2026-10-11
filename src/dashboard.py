"""
CRISP-DM: Deployment - dashboard HTML de la watchlist puntuada.

Lee outputs/watchlist_scored.csv (lo genera src.model si falta) y escribe un HTML
autocontenido (sin servidor, sin dependencias) en:
    outputs/watchlist_dashboard.html  - copia local
    docs/index.html                   - lo que publica GitHub Pages

    python -m src.dashboard
"""

import json
from datetime import date

import pandas as pd

from src.config import CATALOG_SCORED_CSV, DOCS, OUTPUTS, SCORED_CSV

DESTS = [OUTPUTS / "watchlist_dashboard.html", DOCS / "index.html"]

TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Watchlist &mdash; notas predichas</title>
<style>
  :root {{
    --bg: #f7f7f5; --card: #fff; --ink: #1c1c1c; --muted: #6b6b6b;
    --border: #e3e3df; --accent: #2b6cb0;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 24px; background: var(--bg); color: var(--ink);
    font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: var(--muted); margin-bottom: 20px; }}
  .wrap {{ max-width: 1100px; margin: 0 auto; }}
  .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 16px; min-width: 130px; }}
  .card .n {{ font-size: 22px; font-weight: 600; }}
  .card .l {{ color: var(--muted); font-size: 12px; }}
  #chart {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 16px; margin-bottom: 20px; }}
  .bar {{ fill: var(--accent); }}
  .bar-label {{ fill: var(--muted); font-size: 11px; }}
  .controls {{ position: sticky; top: 0; z-index: 5; background: var(--card);
    border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px 14px;
    margin: 0 0 16px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05); }}
  input[type=search] {{ width: 100%; padding: 10px 12px; border: 1px solid var(--border);
    border-radius: 8px; font-size: 16px; background: var(--bg); }}
  .filter-bar {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-end;
    margin-top: 12px; }}
  .filter-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .filter-group > label {{ font-size: 11px; font-weight: 600; color: var(--muted);
    text-transform: uppercase; letter-spacing: 0.03em; }}
  .filter-group select {{ padding: 7px 10px; border: 1px solid var(--border); border-radius: 8px;
    font-size: 14px; background: var(--bg); color: var(--ink); min-width: 150px; }}
  .btn-clear {{ padding: 7px 12px; border-radius: 8px; border: 1px solid transparent;
    background: transparent; color: var(--muted); font-size: 13px; cursor: pointer;
    text-decoration: underline; margin-left: auto; }}
  .btn-clear:hover {{ color: var(--ink); }}
  .multiselect {{ position: relative; }}
  .ms-toggle {{ padding: 7px 10px; border: 1px solid var(--border); border-radius: 8px;
    font-size: 14px; background: var(--bg); color: var(--ink); min-width: 150px;
    text-align: left; cursor: pointer; display: flex; align-items: center;
    justify-content: space-between; gap: 8px; }}
  .ms-toggle::after {{ content: "\\25be"; color: var(--muted); font-size: 11px; }}
  .ms-menu {{ position: absolute; top: calc(100% + 4px); left: 0; z-index: 10; min-width: 220px;
    max-height: 280px; overflow-y: auto; background: var(--card); border: 1px solid var(--border);
    border-radius: 8px; box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12); padding: 6px; }}
  .ms-menu[hidden] {{ display: none; }}
  .ms-option {{ display: flex; align-items: center; gap: 8px; padding: 6px 8px;
    border-radius: 6px; font-size: 13px; cursor: pointer; user-select: none; }}
  .ms-option:hover {{ background: #f0f0ec; }}
  .ms-option input {{ margin: 0; }}
  .ms-all {{ font-weight: 600; }}
  .ms-divider {{ height: 1px; background: var(--border); margin: 4px 2px; }}
  .chip {{ display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px;
    border: 1px solid var(--border); background: var(--card); color: var(--muted);
    cursor: pointer; user-select: none; }}
  .chip.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .chip.mini {{ padding: 2px 7px; font-size: 11px; margin: 1px 3px 1px 0; }}
  .btn-pick {{ padding: 7px 14px; border-radius: 8px; border: 1px solid var(--accent);
    background: var(--accent); color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }}
  .btn-pick:hover {{ opacity: 0.9; }}
  tr.picked td {{ background: #eaf2fb; }}
  @media (max-width: 640px) {{
    .filter-bar {{ flex-direction: column; align-items: stretch; }}
    .filter-group select, .ms-toggle {{ width: 100%; min-width: 0; }}
    .ms-menu {{ left: 0; right: 0; min-width: 0; }}
    .btn-clear {{ margin-left: 0; text-align: left; }}
    .btn-pick {{ width: 100%; }}
  }}
  @media (max-width: 640px) {{
    body {{ padding: 12px; }}
    h1 {{ font-size: 18px; }}
    #chart {{ padding: 10px; }}
    .card {{ min-width: 46%; flex: 1; }}
  }}
  .reco {{ margin: 0 0 16px; }}
  .reco h2 {{ font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.03em; color: var(--muted); margin: 0 0 10px; }}
  .reco-row {{ display: flex; gap: 12px; overflow-x: auto; padding-bottom: 4px; }}
  .reco-card {{ flex: 0 0 112px; cursor: pointer; }}
  .reco-poster {{ width: 112px; height: 168px; object-fit: cover; border-radius: 8px;
    display: block; background: var(--border); }}
  .reco-card .reco-title {{ font-size: 12px; font-weight: 600; margin-top: 6px;
    line-height: 1.3; }}
  .reco-card .reco-meta {{ font-size: 11px; color: var(--muted); margin-top: 4px;
    display: flex; align-items: center; gap: 6px; }}
  .reco-empty {{ color: var(--muted); font-size: 13px; }}
  .tablewrap {{ overflow: auto; max-height: 70vh; border: 1px solid var(--border);
    border-radius: 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card);
    min-width: 720px; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #f0f0ec; cursor: pointer; user-select: none; white-space: nowrap;
    position: sticky; top: 0; z-index: 4; }}
  th.nosort {{ cursor: default; }}
  th.sorted::after {{ content: " \\25be"; }}
  th.asc::after {{ content: " \\25b4"; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:hover td {{ background: #fafaf8; }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-weight: 600;
    color: #fff; font-variant-numeric: tabular-nums; }}
  .genres {{ color: var(--muted); font-size: 12px; }}
  .provider-pill {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px;
    background: #eef2f7; color: var(--ink); border: 1px solid var(--border);
    margin: 1px 3px 1px 0; white-space: nowrap; }}
  .poster {{ width: 40px; height: 60px; object-fit: cover; border-radius: 4px; display: block;
    background: var(--border); }}
  a.title-link {{ color: var(--ink); text-decoration: none; }}
  a.title-link:hover {{ text-decoration: underline; }}
  .foot {{ color: var(--muted); font-size: 12px; margin-top: 16px; }}
  .tabs {{ display: flex; gap: 8px; margin-bottom: 20px; }}
  .tab-btn {{ padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--card); color: var(--muted); font-size: 14px; font-weight: 600;
    cursor: pointer; }}
  .tab-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .panel[hidden] {{ display: none; }}
  .badge-discover {{ display: inline-block; padding: 1px 6px; border-radius: 999px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;
    background: #fff3cd; color: #8a6400; margin-left: 5px; vertical-align: middle; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Watchlist &mdash; notas predichas</h1>
  <div class="sub">Generado el {generated} &middot; {n} t&iacute;tulos en tu watchlist
    &middot; {n_catalog} para descubrir &middot;
    modelo: RandomForest sobre el desv&iacute;o vs IMDb (MAE &asymp; 1.26)</div>

  <div class="tabs">
    <button type="button" class="tab-btn active" data-tab="tabla">Tabla</button>
    <button type="button" class="tab-btn" data-tab="dashboard">Dashboard</button>
  </div>

  <div id="panel-dashboard" class="panel" hidden>
    <div class="cards">
      <div class="card"><div class="n">{n}</div><div class="l">t&iacute;tulos</div></div>
      <div class="card"><div class="n">{mean_pred}</div><div class="l">nota predicha media</div></div>
      <div class="card"><div class="n">{n_ge7}</div><div class="l">con nota predicha &ge; 7</div></div>
      <div class="card"><div class="n">{n_lt5}</div><div class="l">con nota predicha &lt; 5</div></div>
    </div>

    <div id="chart"></div>
  </div>

  <div id="panel-tabla" class="panel">
    <div class="controls">
      <input type="search" id="q" placeholder="Buscar por t&iacute;tulo, director o g&eacute;nero&hellip;">
      <div class="filter-bar">
        <div class="filter-group">
          <label for="fType">Tipo</label>
          <select id="fType"><option value="">Todos</option></select>
        </div>
        <div class="filter-group">
          <label id="fPlatformLabel" for="fPlatformBtn">Plataforma</label>
          <div class="multiselect" id="platformSelect">
            <button type="button" id="fPlatformBtn" class="ms-toggle">Todas</button>
            <div id="fPlatformMenu" class="ms-menu" hidden></div>
          </div>
        </div>
        <div class="filter-group">
          <label id="fGenreLabel" for="fGenreBtn">G&eacute;nero</label>
          <div class="multiselect" id="genreSelect">
            <button type="button" id="fGenreBtn" class="ms-toggle">Todos</button>
            <div id="fGenreMenu" class="ms-menu" hidden></div>
          </div>
        </div>
        <div class="filter-group">
          <label for="fSource">Origen</label>
          <select id="fSource">
            <option value="">Todos</option>
            <option value="mine">Mi lista</option>
            <option value="discover">Para descubrir</option>
          </select>
        </div>
        <button type="button" id="clearFilters" class="btn-clear" hidden>Limpiar filtros</button>
        <button type="button" id="pickForMe" class="btn-pick">Eleg&iacute; por m&iacute;</button>
      </div>
    </div>

    <div class="reco">
      <h2>Te recomendamos</h2>
      <div id="recoRow" class="reco-row"></div>
    </div>

    <div class="tablewrap"><table id="t"><thead><tr>
      <th class="nosort">Poster</th>
      <th data-k="Title">T&iacute;tulo</th>
      <th data-k="Year" class="num">A&ntilde;o</th>
      <th data-k="Title Type">Tipo</th>
      <th data-k="IMDb Rating" class="num">IMDb</th>
      <th data-k="Directors">Director</th>
      <th class="nosort">Duraci&oacute;n</th>
      <th data-k="pred_rating" class="num">Nota predicha</th>
      <th data-k="p_like" class="num">P(&ge;7)</th>
      <th data-k="Genres">G&eacute;neros</th>
      <th class="nosort">Streaming</th>
    </tr></thead><tbody></tbody></table></div>

    <div class="foot">Tomar como <b>orden sugerido</b>, no como veredicto: el error
      t&iacute;pico es &plusmn;1.3 puntos. <code>pred_rating</code> y <code>p_like</code>
      salen de dos modelos distintos y pueden no coincidir.</div>
  </div>
</div>

<script>
const DATA = {data_json};
let sortKey = "pred_rating", sortAsc = false;
let currentRows = [];
const activeGenres = new Set();
const activePlatforms = new Set();

function toggleGenre(g) {{
  if (activeGenres.has(g)) activeGenres.delete(g); else activeGenres.add(g);
  const cb = document.querySelector(`#fGenreMenu input[data-genre="${{CSS.escape(g)}}"]`);
  if (cb) cb.checked = activeGenres.has(g);
  updateGenreButton();
  render();
}}

function updateGenreButton() {{
  const n = activeGenres.size;
  document.getElementById("fGenreBtn").textContent =
    n === 0 ? "Todos" : n === 1 ? [...activeGenres][0] : `${{n}} géneros`;
}}

function togglePlatform(p) {{
  if (activePlatforms.has(p)) activePlatforms.delete(p); else activePlatforms.add(p);
  const cb = document.querySelector(`#fPlatformMenu input[data-platform="${{CSS.escape(p)}}"]`);
  if (cb) cb.checked = activePlatforms.has(p);
  updatePlatformButton();
  render();
}}

function updatePlatformButton() {{
  const n = activePlatforms.size;
  document.getElementById("fPlatformBtn").textContent =
    n === 0 ? "Todas" : n === 1 ? [...activePlatforms][0] : `${{n}} plataformas`;
}}

function colorFor(v) {{
  const t = Math.max(0, Math.min(1, (v - 3) / 5));
  const hue = t * 120;               // 0=rojo, 120=verde
  return `hsl(${{hue}}, 62%, 42%)`;
}}

function posterCell(r) {{
  if (!r.poster_path) return "";
  return `<img class="poster" src="https://image.tmdb.org/t/p/w92${{r.poster_path}}" alt="" loading="lazy">`;
}}

function durationLabel(r) {{
  const isTV = (r["Title Type"] || "").toLowerCase().includes("tv");
  if (isTV && r.n_seasons) {{
    const eps = r.n_episodes ? ` &middot; ${{r.n_episodes}} ep` : "";
    return `${{r.n_seasons}} temp${{eps}}`;
  }}
  if (r.tmdb_runtime) return `${{Math.round(r.tmdb_runtime)}} min`;
  return "";
}}

function providerPills(r) {{
  const list = (r.providers_flatrate || "").split("|").filter(Boolean);
  if (!list.length) return '<span class="genres">no disponible</span>';
  return list.map(p => `<span class="provider-pill">${{p}}</span>`).join("");
}}

function genreChips(r) {{
  const list = (r.Genres || "").split(", ").filter(Boolean);
  return list.map(g => `<span class="chip mini${{activeGenres.has(g) ? " active" : ""}}"
    data-genre="${{g}}">${{g}}</span>`).join("");
}}

function pickWeighted(rows) {{
  const weights = rows.map(r => Math.max(0.01, r.pred_rating) ** 2);
  const total = weights.reduce((a, b) => a + b, 0);
  let x = Math.random() * total;
  for (let i = 0; i < rows.length; i++) {{
    x -= weights[i];
    if (x <= 0) return rows[i];
  }}
  return rows[rows.length - 1];
}}

function highlightRow(key) {{
  const row = document.querySelector(`#t tbody tr[data-key="${{CSS.escape(key)}}"]`);
  if (row) {{
    row.scrollIntoView({{behavior: "smooth", block: "center"}});
    row.classList.add("picked");
    setTimeout(() => row.classList.remove("picked"), 2500);
  }}
}}

const RECO_N = 8;

function renderReco(rows) {{
  const box = document.getElementById("recoRow");
  if (!rows.length) {{
    box.innerHTML = '<span class="reco-empty">Ning&uacute;n t&iacute;tulo cumple los filtros activos.</span>';
    return;
  }}
  const top = [...rows].sort((a, b) => b.pred_rating - a.pred_rating).slice(0, RECO_N);
  box.innerHTML = top.map(r => `
    <div class="reco-card" data-key="${{r.Title}}|${{r.Year}}">
      ${{r.poster_path
        ? `<img class="reco-poster" src="https://image.tmdb.org/t/p/w154${{r.poster_path}}" alt="" loading="lazy">`
        : `<div class="reco-poster"></div>`}}
      <div class="reco-title">${{r.Title}}${{r.in_watchlist ? "" : ' <span class="badge-discover">nuevo</span>'}}</div>
      <div class="reco-meta">
        <span class="pill" style="background:${{colorFor(r.pred_rating)}}">${{r.pred_rating.toFixed(1)}}</span>
        ${{r.Year ?? ""}}
      </div>
    </div>`).join("");
}}

function render() {{
  const q = document.getElementById("q").value.trim().toLowerCase();
  const typeSel = document.getElementById("fType").value;
  const sourceSel = document.getElementById("fSource").value;
  let rows = DATA.filter(r => !q
    || r.Title.toLowerCase().includes(q)
    || (r.Genres || "").toLowerCase().includes(q)
    || (r.Directors || "").toLowerCase().includes(q));
  if (typeSel) rows = rows.filter(r => r["Title Type"] === typeSel);
  if (sourceSel === "mine") rows = rows.filter(r => r.in_watchlist);
  else if (sourceSel === "discover") rows = rows.filter(r => !r.in_watchlist);
  if (activePlatforms.size) rows = rows.filter(r => (r.providers_flatrate || "").split("|").some(p => activePlatforms.has(p)));
  if (activeGenres.size) rows = rows.filter(r => (r.Genres || "").split(", ").some(g => activeGenres.has(g)));

  document.getElementById("clearFilters").hidden =
    !(q || typeSel || sourceSel || activePlatforms.size || activeGenres.size);

  rows.sort((a, b) => {{
    let x = a[sortKey], y = b[sortKey];
    if (typeof x === "string") {{ x = x.toLowerCase(); y = (y || "").toLowerCase(); }}
    return (x < y ? -1 : x > y ? 1 : 0) * (sortAsc ? 1 : -1);
  }});

  currentRows = rows;
  const tb = document.querySelector("#t tbody");
  tb.innerHTML = rows.map(r => `
    <tr data-key="${{r.Title}}|${{r.Year}}">
      <td>${{posterCell(r)}}</td>
      <td><a class="title-link" href="${{r.URL || "#"}}" target="_blank" rel="noopener">${{r.Title}}</a>${{r.in_watchlist ? "" : ' <span class="badge-discover">nuevo</span>'}}</td>
      <td class="num">${{r.Year ?? ""}}</td>
      <td>${{r["Title Type"]}}</td>
      <td class="num" title="${{r["Num Votes"] ? r["Num Votes"].toLocaleString("es-AR") + " votos" : ""}}">${{r["IMDb Rating"] ?? ""}}</td>
      <td class="genres">${{r.Directors ?? ""}}</td>
      <td class="genres">${{durationLabel(r)}}</td>
      <td class="num"><span class="pill" style="background:${{colorFor(r.pred_rating)}}">${{r.pred_rating.toFixed(1)}}</span></td>
      <td class="num">${{(r.p_like * 100).toFixed(0)}}%</td>
      <td>${{genreChips(r)}}</td>
      <td>${{providerPills(r)}}</td>
    </tr>`).join("");

  document.querySelectorAll("#t th[data-k]").forEach(th => {{
    th.classList.remove("sorted", "asc");
    if (th.dataset.k === sortKey) th.classList.add(sortAsc ? "asc" : "sorted");
  }});

  renderReco(rows);
  drawChart(rows);
}}

function drawChart(rows) {{
  const bins = new Array(10).fill(0);
  rows.forEach(r => {{
    const b = Math.max(0, Math.min(9, Math.round(r.pred_rating) - 1));
    bins[b]++;
  }});
  const W = 620, H = 140, pad = 24, bw = (W - pad * 2) / 10;
  const max = Math.max(1, ...bins);
  let svg = `<svg viewBox="0 0 ${{W}} ${{H}}" width="100%" height="${{H}}">`;
  bins.forEach((c, i) => {{
    const h = (H - pad * 2) * c / max;
    const x = pad + i * bw, y = H - pad - h;
    svg += `<rect class="bar" x="${{x + 3}}" y="${{y}}" width="${{bw - 6}}" height="${{h}}" rx="2"/>`;
    svg += `<text class="bar-label" x="${{x + bw / 2}}" y="${{H - pad + 12}}" text-anchor="middle">${{i + 1}}</text>`;
    if (c) svg += `<text class="bar-label" x="${{x + bw / 2}}" y="${{y - 4}}" text-anchor="middle">${{c}}</text>`;
  }});
  svg += `<text class="bar-label" x="${{W / 2}}" y="14" text-anchor="middle">distribuci&oacute;n de la nota predicha (redondeada)</text></svg>`;
  document.getElementById("chart").innerHTML = svg;
}}

function initFilters() {{
  const types = [...new Set(DATA.map(r => r["Title Type"]).filter(Boolean))].sort();
  const sel = document.getElementById("fType");
  types.forEach(t => {{
    const opt = document.createElement("option");
    opt.value = t; opt.textContent = t;
    sel.appendChild(opt);
  }});

  const platforms = [...new Set(DATA.flatMap(r => (r.providers_flatrate || "").split("|").filter(Boolean)))].sort();
  const pmenu = document.getElementById("fPlatformMenu");
  const pAllOpt = document.createElement("div");
  pAllOpt.className = "ms-option ms-all";
  pAllOpt.textContent = "Todas";
  pAllOpt.addEventListener("click", () => {{
    activePlatforms.clear();
    pmenu.querySelectorAll("input[data-platform]").forEach(cb => cb.checked = false);
    updatePlatformButton();
    render();
  }});
  pmenu.appendChild(pAllOpt);
  const pDivider = document.createElement("div");
  pDivider.className = "ms-divider";
  pmenu.appendChild(pDivider);
  platforms.forEach(p => {{
    const opt = document.createElement("label");
    opt.className = "ms-option";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.dataset.platform = p;
    cb.addEventListener("change", () => togglePlatform(p));
    opt.appendChild(cb);
    opt.appendChild(document.createTextNode(p));
    pmenu.appendChild(opt);
  }});

  const genres = [...new Set(DATA.flatMap(r => (r.Genres || "").split(", ").filter(Boolean)))].sort();
  const menu = document.getElementById("fGenreMenu");
  const allOpt = document.createElement("div");
  allOpt.className = "ms-option ms-all";
  allOpt.textContent = "Todos";
  allOpt.addEventListener("click", () => {{
    activeGenres.clear();
    menu.querySelectorAll("input[data-genre]").forEach(cb => cb.checked = false);
    updateGenreButton();
    render();
  }});
  menu.appendChild(allOpt);
  const divider = document.createElement("div");
  divider.className = "ms-divider";
  menu.appendChild(divider);
  genres.forEach(g => {{
    const opt = document.createElement("label");
    opt.className = "ms-option";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.dataset.genre = g;
    cb.addEventListener("change", () => toggleGenre(g));
    opt.appendChild(cb);
    opt.appendChild(document.createTextNode(g));
    menu.appendChild(opt);
  }});
}}

document.querySelectorAll("#t th[data-k]").forEach(th => th.addEventListener("click", () => {{
  const k = th.dataset.k;
  if (k === sortKey) sortAsc = !sortAsc;
  else {{ sortKey = k; sortAsc = false; }}
  render();
}}));
document.getElementById("q").addEventListener("input", render);
document.getElementById("fType").addEventListener("change", render);
document.getElementById("fSource").addEventListener("change", render);
document.querySelector("#t tbody").addEventListener("click", (e) => {{
  const chip = e.target.closest(".chip[data-genre]");
  if (chip) toggleGenre(chip.dataset.genre);
}});
document.getElementById("clearFilters").addEventListener("click", () => {{
  document.getElementById("q").value = "";
  document.getElementById("fType").value = "";
  document.getElementById("fSource").value = "";
  activePlatforms.clear();
  document.querySelectorAll("#fPlatformMenu input[data-platform]").forEach(cb => cb.checked = false);
  updatePlatformButton();
  activeGenres.clear();
  document.querySelectorAll("#fGenreMenu input[data-genre]").forEach(cb => cb.checked = false);
  updateGenreButton();
  render();
}});
document.getElementById("fGenreBtn").addEventListener("click", (e) => {{
  e.stopPropagation();
  document.getElementById("fGenreMenu").hidden = !document.getElementById("fGenreMenu").hidden;
}});
document.getElementById("fPlatformBtn").addEventListener("click", (e) => {{
  e.stopPropagation();
  document.getElementById("fPlatformMenu").hidden = !document.getElementById("fPlatformMenu").hidden;
}});
document.addEventListener("click", (e) => {{
  if (!document.getElementById("genreSelect").contains(e.target)) {{
    document.getElementById("fGenreMenu").hidden = true;
  }}
  if (!document.getElementById("platformSelect").contains(e.target)) {{
    document.getElementById("fPlatformMenu").hidden = true;
  }}
}});
document.getElementById("pickForMe").addEventListener("click", () => {{
  if (!currentRows.length) return;
  const pick = pickWeighted(currentRows);
  highlightRow(pick.Title + "|" + pick.Year);
}});
document.getElementById("recoRow").addEventListener("click", (e) => {{
  const card = e.target.closest(".reco-card");
  if (card) highlightRow(card.dataset.key);
}});

document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => {{
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b === btn));
  document.getElementById("panel-dashboard").hidden = btn.dataset.tab !== "dashboard";
  document.getElementById("panel-tabla").hidden = btn.dataset.tab !== "tabla";
}}));

initFilters();
render();
</script>
</body>
</html>
"""


def build_html() -> None:
    if not SCORED_CSV.exists():
        from src.model import score_watchlist
        score_watchlist()

    df = pd.read_csv(SCORED_CSV)
    df["in_watchlist"] = True

    cat = pd.read_csv(CATALOG_SCORED_CSV) if CATALOG_SCORED_CSV.exists() else pd.DataFrame()
    if not cat.empty:
        cat["in_watchlist"] = False
    combined = pd.concat([df, cat], ignore_index=True) if not cat.empty else df

    html = TEMPLATE.format(
        generated=date.today().isoformat(),
        n=len(df),
        n_catalog=len(cat),
        mean_pred=round(df["pred_rating"].mean(), 1),
        n_ge7=int((df["pred_rating"] >= 7).sum()),
        n_lt5=int((df["pred_rating"] < 5).sum()),
        data_json=json.dumps(json.loads(combined.to_json(orient="records")), ensure_ascii=False),
    )
    for dest in DESTS:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        print(f"Dashboard: {dest}")
    (DOCS / ".nojekyll").touch()
    print("Local: abrir con doble clic. Pages: 'make publish' actualiza el sitio.")


if __name__ == "__main__":
    build_html()
