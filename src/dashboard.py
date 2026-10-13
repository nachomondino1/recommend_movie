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

from src.config import (CATALOG_SCORED_CSV, DOCS, OUTPUTS,
                        SCORED_CSV, WATCHED_SCORED_CSV)
from src.taste import build_taste_stats

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
  .traj-head {{ font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.03em; color: var(--muted); margin: 0 0 10px; }}
  .traj-grid {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
  .chart-card {{ flex: 1; min-width: 260px; background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px; }}
  .traj-title {{ font-size: 12px; color: var(--muted); margin-bottom: 8px; }}
  .traj-empty {{ font-size: 13px; color: var(--muted); }}
  .hbar {{ display: flex; align-items: center; gap: 8px; margin-bottom: 7px; }}
  .hbar-label {{ flex: 0 0 120px; font-size: 13px; overflow: hidden; text-overflow: ellipsis;
    white-space: nowrap; }}
  .hbar-track {{ flex: 1; background: var(--bg); border-radius: 4px; height: 14px; overflow: hidden; }}
  .hbar-fill {{ height: 100%; border-radius: 4px; }}
  .hbar-value {{ flex: 0 0 64px; text-align: right; color: var(--muted); font-size: 12px;
    font-variant-numeric: tabular-nums; }}
  .toplist-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .toplist-info {{ flex: 1; min-width: 0; }}
  .toplist-info a {{ display: block; font-weight: 600; font-size: 13px; }}
  .controls {{ position: sticky; top: 0; z-index: 5; background: var(--card);
    border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px 14px;
    margin: 0 0 16px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05); }}
  input[type=search] {{ width: 100%; padding: 10px 12px; border: 1px solid var(--border);
    border-radius: 8px; font-size: 16px; background: var(--bg); }}
  .result-count {{ color: var(--muted); font-size: 12px; margin-top: 8px; }}
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
  @media (max-height: 480px) {{
    .controls {{ position: static; }}
  }}
  @media (max-width: 640px) {{
    .controls {{ position: static; }}
    .filter-bar {{ flex-direction: column; align-items: stretch; }}
    .filter-group select, .ms-toggle {{ width: 100%; min-width: 0; }}
    .ms-menu {{ left: 0; right: 0; min-width: 0; }}
    .btn-clear {{ margin-left: 0; text-align: left; }}
  }}
  @media (max-width: 640px) {{
    body {{ padding: 12px; }}
    h1 {{ font-size: 18px; }}
    #chart {{ padding: 10px; }}
    .card {{ min-width: 46%; flex: 1; }}
  }}
  .reco {{ margin: 0 0 16px; }}
  .reco-head {{ display: flex; align-items: center; justify-content: space-between;
    gap: 8px 12px; flex-wrap: wrap; margin: 0 0 10px; }}
  .reco h2 {{ font-size: 13px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.03em; color: var(--muted); margin: 0; }}
  .reco-row {{ display: flex; gap: 12px; overflow-x: auto; padding-bottom: 4px; }}
  .reco-card {{ flex: 0 0 112px; cursor: pointer; }}
  .reco-poster {{ width: 112px; height: 168px; object-fit: cover; border-radius: 8px;
    display: block; background: var(--border); }}
  .reco-card .reco-title {{ font-size: 12px; font-weight: 600; margin-top: 6px;
    line-height: 1.3; }}
  .reco-card .reco-meta {{ font-size: 11px; color: var(--muted); margin-top: 4px;
    display: flex; align-items: center; gap: 6px; }}
  .reco-empty {{ color: var(--muted); font-size: 13px; }}
  .empty-state {{ text-align: center; color: var(--muted); font-size: 13px; padding: 28px 12px; }}
  .tablewrap {{ overflow: auto; max-height: 70vh; border: 1px solid var(--border);
    border-radius: 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card);
    min-width: 720px; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--border);
    vertical-align: top; }}
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
  .mobile-meta {{ display: none; }}
  .foot {{ color: var(--muted); font-size: 12px; margin-top: 16px; }}
  @media (max-width: 640px) {{
    table {{ min-width: 0; }}
    .tablewrap {{ overflow-x: hidden; }}
    th, td {{ padding-left: 4px; padding-right: 4px; }}
    th {{ white-space: normal; }}
    .mobile-chips .provider-pill {{ white-space: normal; }}
    .col-year, .col-type, .col-imdb, .col-director, .col-duration,
    .col-genres, .col-streaming {{ display: none; }}
    .mobile-meta {{ display: block; margin-top: 4px; }}
    .mobile-meta-line {{ color: var(--muted); font-size: 12px; }}
    .mobile-chips {{ margin-top: 4px; }}
  }}
  .tabs {{ display: flex; gap: 8px; margin-bottom: 20px; }}
  .tab-btn {{ padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--card); color: var(--muted); font-size: 14px; font-weight: 600;
    cursor: pointer; }}
  .tab-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
  .panel[hidden] {{ display: none; }}
  .badge-discover {{ display: inline-block; padding: 1px 6px; border-radius: 999px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.02em;
    background: #fff3cd; color: #8a6400; margin-left: 5px; vertical-align: middle; }}
  .title-btn {{ background: none; border: none; padding: 0; margin: 0; font: inherit;
    color: var(--ink); cursor: pointer; text-align: left; }}
  .title-btn:hover {{ text-decoration: underline; }}
  .imdb-link {{ color: var(--muted); font-size: 11px; text-decoration: none; margin-left: 5px; }}
  .imdb-link:hover {{ text-decoration: underline; }}
  .modal-overlay {{ position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); display: flex;
    align-items: center; justify-content: center; padding: 16px; z-index: 50; }}
  .modal-overlay[hidden] {{ display: none; }}
  .modal-box {{ background: var(--card); border-radius: 12px; max-width: 560px; width: 100%;
    max-height: 85vh; overflow-y: auto; padding: 20px; position: relative; }}
  .modal-close {{ position: absolute; top: 8px; right: 10px; background: none; border: none;
    font-size: 24px; line-height: 1; color: var(--muted); cursor: pointer; padding: 6px; }}
  .modal-close:hover {{ color: var(--ink); }}
  .modal-head {{ display: flex; gap: 14px; margin-bottom: 14px; padding-right: 22px; }}
  .modal-poster {{ width: 92px; height: 138px; object-fit: cover; border-radius: 6px; flex: none;
    background: var(--border); }}
  .modal-head h3 {{ margin: 0 0 4px; font-size: 16px; }}
  .modal-meta {{ color: var(--muted); font-size: 12px; }}
  .modal-section-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.03em; color: var(--muted); margin-bottom: 4px; }}
  .modal-overview {{ margin-bottom: 4px; }}
  .modal-overview p {{ margin: 0 0 10px; white-space: pre-wrap; }}
  .modal-review {{ margin-bottom: 10px; padding-left: 10px; border-left: 3px solid var(--border); }}
  .modal-review p {{ margin: 0; white-space: pre-wrap; }}
  .modal-review-pos {{ border-left-color: #2f9e44; }}
  .modal-review-neg {{ border-left-color: #e03131; }}
  .modal-review-empty {{ border-left: none; padding-left: 0; }}
  .modal-review-empty p {{ color: var(--muted); margin-bottom: 6px; }}
  .modal-review-empty code {{ display: block; background: var(--bg); border: 1px solid var(--border);
    border-radius: 6px; padding: 6px 8px; font-size: 12px; overflow-x: auto; }}
  .modal-review-date {{ color: var(--muted); font-size: 11px; margin-top: 2px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Watchlist &mdash; notas predichas</h1>
  <div class="sub">Generado el {generated} &middot; {n} t&iacute;tulos en tu watchlist
    &middot; {n_catalog} para descubrir &middot; {n_watched} ya vistas</div>

  <div class="tabs">
    <button type="button" class="tab-btn active" data-tab="hoy">&iquest;Qu&eacute; ver hoy?</button>
    <button type="button" class="tab-btn" data-tab="analisis">An&aacute;lisis</button>
    <button type="button" class="tab-btn" data-tab="catalogo">Cat&aacute;logo</button>
  </div>

  <div id="panel-analisis" class="panel" hidden>
    <div class="cards">
      <div class="card"><div class="n">{t_n_rated}</div><div class="l">t&iacute;tulos puntuados</div></div>
      <div class="card"><div class="n">{t_movies_series}</div><div class="l">pel&iacute;culas / series</div></div>
      <div class="card"><div class="n">{t_mean_rating}</div><div class="l">nota media que pon&eacute;s</div></div>
      <div class="card"><div class="n">{t_deviation}</div><div class="l">vs. nota de IMDb (promedio)</div></div>
    </div>

    <div id="chart">
      <div class="traj-title">distribuci&oacute;n de tus notas (1 a 10)</div>
      <div id="chartSvg"></div>
    </div>

    <div class="traj-head">Tu patr&oacute;n de gusto</div>
    <div class="traj-grid">
      <div class="chart-card">
        <div class="traj-title">por g&eacute;nero &mdash; nota media (m&iacute;n. 3 t&iacute;tulos)</div>
        <div id="rankGenre"></div>
      </div>
      <div class="chart-card">
        <div class="traj-title">por d&eacute;cada de estreno</div>
        <div id="chartDecade"></div>
      </div>
    </div>
    <div class="traj-grid">
      <div class="chart-card">
        <div class="traj-title">pel&iacute;culas vs. series</div>
        <div id="rankType"></div>
      </div>
      <div class="chart-card">
        <div class="traj-title">directores que m&aacute;s te gustan (m&iacute;n. 2 t&iacute;tulos)</div>
        <div id="rankDirector"></div>
      </div>
    </div>
    <div class="traj-grid">
      <div class="chart-card">
        <div class="traj-title">tus mejor puntuadas</div>
        <div id="topList"></div>
      </div>
      <div class="chart-card">
        <div class="traj-title">tus peor puntuadas</div>
        <div id="bottomList"></div>
      </div>
    </div>
  </div>

  <div id="panel-hoy" class="panel">
    <div class="controls">
      <input type="search" id="q" placeholder="Buscar por t&iacute;tulo, director o g&eacute;nero&hellip;">
      <div id="resultCount" class="result-count"></div>
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
      </div>
    </div>

    <div class="reco">
      <div class="reco-head">
        <h2>Te recomendamos</h2>
        <button type="button" id="pickForMe" class="btn-pick">Eleg&iacute; por m&iacute;</button>
      </div>
      <div id="recoRow" class="reco-row"></div>
    </div>

    <div class="tablewrap"><table id="t"><thead><tr>
      <th class="nosort">Poster</th>
      <th data-k="Title">T&iacute;tulo</th>
      <th data-k="pred_rating" class="num">Nota predicha</th>
      <th data-k="p_like" class="num">P(&ge;7)</th>
      <th class="nosort col-streaming">Streaming</th>
      <th data-k="Genres" class="col-genres">G&eacute;neros</th>
      <th data-k="Year" class="num col-year">A&ntilde;o</th>
      <th data-k="Title Type" class="col-type">Tipo</th>
      <th data-k="IMDb Rating" class="num col-imdb">IMDb</th>
      <th data-k="Directors" class="col-director">Director</th>
      <th class="nosort col-duration">Duraci&oacute;n</th>
    </tr></thead><tbody></tbody></table></div>

    <div class="foot">Tomar como <b>orden sugerido</b>, no como veredicto: el error
      t&iacute;pico es &plusmn;1.3 puntos. <code>pred_rating</code> y <code>p_like</code>
      salen de dos modelos distintos y pueden no coincidir.</div>
  </div>

  <div id="panel-catalogo" class="panel" hidden>
    <div class="controls">
      <input type="search" id="qCat" placeholder="Buscar por t&iacute;tulo, director o g&eacute;nero&hellip;">
      <div id="resultCountCat" class="result-count"></div>
      <div class="filter-bar">
        <div class="filter-group">
          <label for="fTypeCat">Tipo</label>
          <select id="fTypeCat"><option value="">Todos</option></select>
        </div>
        <button type="button" id="clearFiltersCat" class="btn-clear" hidden>Limpiar filtros</button>
      </div>
    </div>

    <div class="tablewrap"><table id="tCat"><thead><tr>
      <th class="nosort">Poster</th>
      <th data-k="Title">T&iacute;tulo</th>
      <th data-k="pred_rating" class="num">Tu nota</th>
      <th data-k="Year" class="num col-year">A&ntilde;o</th>
      <th data-k="Title Type" class="col-type">Tipo</th>
      <th data-k="Genres" class="col-genres">G&eacute;neros</th>
      <th data-k="IMDb Rating" class="num col-imdb">IMDb</th>
      <th data-k="Directors" class="col-director">Director</th>
      <th class="nosort col-duration">Duraci&oacute;n</th>
    </tr></thead><tbody></tbody></table></div>

    <div class="foot">Tu cat&aacute;logo de t&iacute;tulos ya vistos y puntuados en IMDb.
      Clic en el t&iacute;tulo para ver la sinopsis y tu rese&ntilde;a (si la escribiste).</div>
  </div>
</div>

<div id="modalOverlay" class="modal-overlay" hidden>
  <div class="modal-box">
    <button type="button" id="modalClose" class="modal-close" aria-label="Cerrar">&times;</button>
    <div id="modalBody"></div>
  </div>
</div>

<script>
const DATA = {data_json};
const HOY_DATA = DATA.filter(r => !r.watched);
const CATALOG_DATA = DATA.filter(r => r.watched);
const TASTE = {taste_json};
let sortKey = "pred_rating", sortAsc = false;
let catSortKey = "pred_rating", catSortAsc = false;
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

function discoverBadge(r) {{
  return r.in_watchlist ? "" : ' <span class="badge-discover">nuevo</span>';
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

function mobileMetaLine(r) {{
  const parts = [];
  if (r.Year) parts.push(r.Year);
  if (r["Title Type"]) parts.push(r["Title Type"]);
  if (r["IMDb Rating"] != null) parts.push("IMDb " + r["IMDb Rating"]);
  if (r.Directors) parts.push(r.Directors);
  const dur = durationLabel(r);
  if (dur) parts.push(dur);
  return parts.join(" &middot; ");
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

function escapeHtml(s) {{
  return (s || "").replace(/[&<>"']/g, c => ({{
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }}[c]));
}}

function reviewSectionsHtml(r) {{
  const liked = r.my_liked ? `<div class="modal-review modal-review-pos">
      <div class="modal-section-label">Te gust&oacute;</div>
      <p>${{escapeHtml(r.my_liked)}}</p></div>` : "";
  const disliked = r.my_disliked ? `<div class="modal-review modal-review-neg">
      <div class="modal-section-label">No te gust&oacute;</div>
      <p>${{escapeHtml(r.my_disliked)}}</p></div>` : "";
  if (!liked && !disliked) {{
    return `<div class="modal-review modal-review-empty">
      <div class="modal-section-label">Tu rese&ntilde;a</div>
      <p>Todav&iacute;a no dejaste una rese&ntilde;a para este t&iacute;tulo.</p>
      <code>make review TITLE="${{escapeHtml(r.Title)}}" LIKED="..." DISLIKED="..."</code></div>`;
  }}
  const date = r.review_date ? `<div class="modal-review-date">${{r.review_date}}</div>` : "";
  return liked + disliked + date;
}}

function openModal(key) {{
  const r = DATA.find(d => (d.Title + "|" + d.Year) === key);
  if (!r) return;
  const poster = r.poster_path
    ? `<img class="modal-poster" src="https://image.tmdb.org/t/p/w185${{r.poster_path}}" alt="">`
    : `<div class="modal-poster"></div>`;
  const overviewText = escapeHtml(r.overview) || "Sin sinopsis.";
  const reviewBlock = reviewSectionsHtml(r);
  document.getElementById("modalBody").innerHTML = `
    <div class="modal-head">
      ${{poster}}
      <div>
        <h3>${{escapeHtml(r.Title)}}</h3>
        <div class="modal-meta">${{mobileMetaLine(r)}}</div>
      </div>
    </div>
    <div class="modal-overview">
      <div class="modal-section-label">Sinopsis</div>
      <p>${{overviewText}}</p>
    </div>
    ${{reviewBlock}}`;
  document.getElementById("modalOverlay").hidden = false;
}}

function closeModal() {{
  document.getElementById("modalOverlay").hidden = true;
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
      <div class="reco-title">${{r.Title}}${{discoverBadge(r)}}</div>
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
  let rows = HOY_DATA.filter(r => !q
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
  document.getElementById("resultCount").innerHTML = rows.length === HOY_DATA.length
    ? `${{rows.length}} t&iacute;tulos`
    : `${{rows.length}} de ${{HOY_DATA.length}} t&iacute;tulos`;

  rows.sort((a, b) => {{
    let x = a[sortKey], y = b[sortKey];
    if (typeof x === "string") {{ x = x.toLowerCase(); y = (y || "").toLowerCase(); }}
    return (x < y ? -1 : x > y ? 1 : 0) * (sortAsc ? 1 : -1);
  }});

  currentRows = rows;
  const tb = document.querySelector("#t tbody");
  tb.innerHTML = !rows.length
    ? `<tr><td colspan="11" class="empty-state">Ning&uacute;n t&iacute;tulo cumple los filtros activos.</td></tr>`
    : rows.map(r => {{
    const genres = genreChips(r);
    const providers = providerPills(r);
    const meta = mobileMetaLine(r);
    return `
    <tr data-key="${{r.Title}}|${{r.Year}}">
      <td>${{posterCell(r)}}</td>
      <td>
        <button type="button" class="title-btn" data-key="${{r.Title}}|${{r.Year}}">${{r.Title}}</button>
        <a class="imdb-link" href="${{r.URL || "#"}}" target="_blank" rel="noopener" title="Abrir en IMDb">IMDb &#8599;</a>${{discoverBadge(r)}}
        <div class="mobile-meta">
          ${{meta ? `<div class="mobile-meta-line">${{meta}}</div>` : ""}}
          <div class="mobile-chips">${{genres}}</div>
          <div class="mobile-chips">${{providers}}</div>
        </div>
      </td>
      <td class="num"><span class="pill" style="background:${{colorFor(r.pred_rating)}}">${{r.pred_rating.toFixed(1)}}</span></td>
      <td class="num">${{(r.p_like * 100).toFixed(0)}}%</td>
      <td class="col-streaming">${{providers}}</td>
      <td class="col-genres">${{genres}}</td>
      <td class="num col-year">${{r.Year ?? ""}}</td>
      <td class="col-type">${{r["Title Type"]}}</td>
      <td class="num col-imdb" title="${{r["Num Votes"] ? r["Num Votes"].toLocaleString("es-AR") + " votos" : ""}}">${{r["IMDb Rating"] ?? ""}}</td>
      <td class="genres col-director">${{r.Directors ?? ""}}</td>
      <td class="genres col-duration">${{durationLabel(r)}}</td>
    </tr>`;
  }}).join("");

  document.querySelectorAll("#t th[data-k]").forEach(th => {{
    th.classList.remove("sorted", "asc");
    if (th.dataset.k === sortKey) th.classList.add(sortAsc ? "asc" : "sorted");
  }});

  renderReco(rows);
}}

function hbarList(containerId, items) {{
  const el = document.getElementById(containerId);
  if (!items.length) {{
    el.innerHTML = '<div class="traj-empty">Todav&iacute;a no hay suficientes t&iacute;tulos.</div>';
    return;
  }}
  el.innerHTML = items.map(it => `
    <div class="hbar">
      <div class="hbar-label" title="${{it.label}}">${{it.label}}</div>
      <div class="hbar-track"><div class="hbar-fill"
        style="width:${{it.avg * 10}}%;background:${{colorFor(it.avg)}}"></div></div>
      <div class="hbar-value">${{it.avg.toFixed(1)}} &middot; ${{it.n}}</div>
    </div>`).join("");
}}

function drawRatingHistogram(containerId, counts) {{
  const mount = document.getElementById(containerId);
  const W = mount.clientWidth || 620, H = 140, pad = 24, bw = (W - pad * 2) / 10;
  const max = Math.max(1, ...counts);
  let svg = `<svg viewBox="0 0 ${{W}} ${{H}}" width="100%" height="${{H}}">`;
  counts.forEach((c, i) => {{
    const h = (H - pad * 2) * c / max;
    const x = pad + i * bw, y = H - pad - h;
    svg += `<rect class="bar" x="${{x + 3}}" y="${{y}}" width="${{bw - 6}}" height="${{h}}" rx="2"/>`;
    svg += `<text class="bar-label" x="${{x + bw / 2}}" y="${{H - pad + 12}}" text-anchor="middle">${{i + 1}}</text>`;
    if (c) svg += `<text class="bar-label" x="${{x + bw / 2}}" y="${{y - 4}}" text-anchor="middle">${{c}}</text>`;
  }});
  svg += `</svg>`;
  mount.innerHTML = svg;
}}

function drawDecadeChart(containerId, items) {{
  const mount = document.getElementById(containerId);
  if (!items.length) {{
    mount.innerHTML = '<div class="traj-empty">Todav&iacute;a no hay suficientes t&iacute;tulos.</div>';
    return;
  }}
  const W = mount.clientWidth || 300, H = 140, pad = 24, bw = (W - pad * 2) / items.length;
  let svg = `<svg viewBox="0 0 ${{W}} ${{H}}" width="100%" height="${{H}}">`;
  items.forEach((it, i) => {{
    const h = (H - pad * 2) * it.avg / 10;
    const x = pad + i * bw, y = H - pad - h;
    svg += `<rect class="bar" x="${{x + 3}}" y="${{y}}" width="${{bw - 6}}" height="${{h}}" rx="2"
      style="fill:${{colorFor(it.avg)}}"/>`;
    svg += `<text class="bar-label" x="${{x + bw / 2}}" y="${{H - pad + 12}}" text-anchor="middle">${{it.decade}}</text>`;
    svg += `<text class="bar-label" x="${{x + bw / 2}}" y="${{y - 4}}" text-anchor="middle">${{it.avg.toFixed(1)}}</text>`;
  }});
  svg += `</svg>`;
  mount.innerHTML = svg;
}}

function titleList(containerId, items) {{
  const el = document.getElementById(containerId);
  if (!items.length) {{
    el.innerHTML = '<div class="traj-empty">Sin datos todav&iacute;a.</div>';
    return;
  }}
  el.innerHTML = items.map(it => `
    <div class="toplist-row">
      ${{it.poster_path
        ? `<img class="poster" src="https://image.tmdb.org/t/p/w92${{it.poster_path}}" alt="" loading="lazy">`
        : `<div class="poster"></div>`}}
      <div class="toplist-info">
        <a class="title-link" href="${{it.URL || "#"}}" target="_blank" rel="noopener">${{it.Title}}</a>
        <div class="genres">${{it.Year ?? ""}} &middot; ${{it.Genres ?? ""}}</div>
      </div>
      <span class="pill" style="background:${{colorFor(it["Your Rating"])}}">${{it["Your Rating"]}}</span>
    </div>`).join("");
}}

function renderTaste() {{
  drawRatingHistogram("chartSvg", TASTE.rating_counts);
  hbarList("rankGenre", TASTE.by_genre);
  hbarList("rankType", TASTE.by_type);
  hbarList("rankDirector", TASTE.by_director);
  drawDecadeChart("chartDecade", TASTE.by_decade);
  titleList("topList", TASTE.top);
  titleList("bottomList", TASTE.bottom);
}}

function initFilters() {{
  const types = [...new Set(HOY_DATA.map(r => r["Title Type"]).filter(Boolean))].sort();
  const sel = document.getElementById("fType");
  types.forEach(t => {{
    const opt = document.createElement("option");
    opt.value = t; opt.textContent = t;
    sel.appendChild(opt);
  }});

  const platforms = [...new Set(HOY_DATA.flatMap(r => (r.providers_flatrate || "").split("|").filter(Boolean)))].sort();
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

  const genres = [...new Set(HOY_DATA.flatMap(r => (r.Genres || "").split(", ").filter(Boolean)))].sort();
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

function renderCatalog() {{
  const q = document.getElementById("qCat").value.trim().toLowerCase();
  const typeSel = document.getElementById("fTypeCat").value;
  let rows = CATALOG_DATA.filter(r => !q
    || r.Title.toLowerCase().includes(q)
    || (r.Genres || "").toLowerCase().includes(q)
    || (r.Directors || "").toLowerCase().includes(q));
  if (typeSel) rows = rows.filter(r => r["Title Type"] === typeSel);

  document.getElementById("clearFiltersCat").hidden = !(q || typeSel);
  document.getElementById("resultCountCat").innerHTML = rows.length === CATALOG_DATA.length
    ? `${{rows.length}} t&iacute;tulos`
    : `${{rows.length}} de ${{CATALOG_DATA.length}} t&iacute;tulos`;

  rows.sort((a, b) => {{
    let x = a[catSortKey], y = b[catSortKey];
    if (typeof x === "string") {{ x = x.toLowerCase(); y = (y || "").toLowerCase(); }}
    return (x < y ? -1 : x > y ? 1 : 0) * (catSortAsc ? 1 : -1);
  }});

  const tb = document.querySelector("#tCat tbody");
  tb.innerHTML = !rows.length
    ? `<tr><td colspan="9" class="empty-state">Ning&uacute;n t&iacute;tulo cumple los filtros activos.</td></tr>`
    : rows.map(r => {{
    const meta = mobileMetaLine(r);
    return `
    <tr data-key="${{r.Title}}|${{r.Year}}">
      <td>${{posterCell(r)}}</td>
      <td>
        <button type="button" class="title-btn" data-key="${{r.Title}}|${{r.Year}}">${{r.Title}}</button>
        <a class="imdb-link" href="${{r.URL || "#"}}" target="_blank" rel="noopener" title="Abrir en IMDb">IMDb &#8599;</a>
        <div class="mobile-meta">
          ${{meta ? `<div class="mobile-meta-line">${{meta}}</div>` : ""}}
          ${{r.Genres ? `<div class="mobile-meta-line">${{r.Genres}}</div>` : ""}}
        </div>
      </td>
      <td class="num"><span class="pill" style="background:${{colorFor(r.pred_rating)}}">${{r.pred_rating.toFixed(1)}}</span></td>
      <td class="num col-year">${{r.Year ?? ""}}</td>
      <td class="col-type">${{r["Title Type"]}}</td>
      <td class="genres col-genres">${{r.Genres ?? ""}}</td>
      <td class="num col-imdb">${{r["IMDb Rating"] ?? ""}}</td>
      <td class="genres col-director">${{r.Directors ?? ""}}</td>
      <td class="genres col-duration">${{durationLabel(r)}}</td>
    </tr>`;
  }}).join("");

  document.querySelectorAll("#tCat th[data-k]").forEach(th => {{
    th.classList.remove("sorted", "asc");
    if (th.dataset.k === catSortKey) th.classList.add(catSortAsc ? "asc" : "sorted");
  }});
}}

function initCatalogFilters() {{
  const types = [...new Set(CATALOG_DATA.map(r => r["Title Type"]).filter(Boolean))].sort();
  const sel = document.getElementById("fTypeCat");
  types.forEach(t => {{
    const opt = document.createElement("option");
    opt.value = t; opt.textContent = t;
    sel.appendChild(opt);
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
  if (chip) {{ toggleGenre(chip.dataset.genre); return; }}
  const btn = e.target.closest(".title-btn");
  if (btn) openModal(btn.dataset.key);
}});
document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("modalOverlay").addEventListener("click", (e) => {{
  if (e.target.id === "modalOverlay") closeModal();
}});
document.addEventListener("keydown", (e) => {{
  if (e.key === "Escape") closeModal();
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

document.querySelectorAll("#tCat th[data-k]").forEach(th => th.addEventListener("click", () => {{
  const k = th.dataset.k;
  if (k === catSortKey) catSortAsc = !catSortAsc;
  else {{ catSortKey = k; catSortAsc = false; }}
  renderCatalog();
}}));
document.getElementById("qCat").addEventListener("input", renderCatalog);
document.getElementById("fTypeCat").addEventListener("change", renderCatalog);
document.querySelector("#tCat tbody").addEventListener("click", (e) => {{
  const btn = e.target.closest(".title-btn");
  if (btn) openModal(btn.dataset.key);
}});
document.getElementById("clearFiltersCat").addEventListener("click", () => {{
  document.getElementById("qCat").value = "";
  document.getElementById("fTypeCat").value = "";
  renderCatalog();
}});

document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => {{
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b === btn));
  document.getElementById("panel-hoy").hidden = btn.dataset.tab !== "hoy";
  document.getElementById("panel-analisis").hidden = btn.dataset.tab !== "analisis";
  document.getElementById("panel-catalogo").hidden = btn.dataset.tab !== "catalogo";
  if (btn.dataset.tab === "analisis") renderTaste();
}}));

window.addEventListener("resize", () => {{
  if (!document.getElementById("panel-analisis").hidden) renderTaste();
}});

initFilters();
render();
renderTaste();
initCatalogFilters();
renderCatalog();
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
    df["watched"] = False

    cat = pd.read_csv(CATALOG_SCORED_CSV) if CATALOG_SCORED_CSV.exists() else pd.DataFrame()
    if not cat.empty:
        cat["in_watchlist"] = False
        cat["watched"] = False

    watched = pd.read_csv(WATCHED_SCORED_CSV) if WATCHED_SCORED_CSV.exists() else pd.DataFrame()
    if not watched.empty:
        watched["in_watchlist"] = False
        watched["watched"] = True

    combined = pd.concat([d for d in (df, cat, watched) if not d.empty], ignore_index=True)

    taste = build_taste_stats()

    html = TEMPLATE.format(
        generated=date.today().isoformat(),
        n=len(df),
        n_catalog=len(cat),
        n_watched=len(watched),
        t_n_rated=taste["n_rated"],
        t_movies_series=f'{taste["n_movies"]} / {taste["n_series"]}',
        t_mean_rating=taste["mean_rating"],
        t_deviation=f'{taste["deviation_vs_imdb"]:+.2f}',
        data_json=json.dumps(json.loads(combined.to_json(orient="records")), ensure_ascii=False),
        taste_json=json.dumps(taste, ensure_ascii=False),
    )
    for dest in DESTS:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        print(f"Dashboard: {dest}")
    (DOCS / ".nojekyll").touch()
    print("Local: abrir con doble clic. Pages: 'make publish' actualiza el sitio.")


if __name__ == "__main__":
    build_html()
