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

from src.config import DOCS, OUTPUTS, SCORED_CSV

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
  input[type=search] {{ width: 100%; padding: 10px 12px; border: 1px solid var(--border);
    border-radius: 8px; font-size: 16px; margin-bottom: 12px; background: var(--card);
    position: sticky; top: 8px; z-index: 5; }}
  @media (max-width: 640px) {{
    body {{ padding: 12px; }}
    h1 {{ font-size: 18px; }}
    #chart {{ padding: 10px; }}
    .card {{ min-width: 46%; flex: 1; }}
  }}
  .tablewrap {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card);
    min-width: 720px; }}
  th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: #f0f0ec; cursor: pointer; user-select: none; white-space: nowrap; }}
  th.sorted::after {{ content: " \\25be"; }}
  th.asc::after {{ content: " \\25b4"; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:hover td {{ background: #fafaf8; }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-weight: 600;
    color: #fff; font-variant-numeric: tabular-nums; }}
  .genres {{ color: var(--muted); font-size: 12px; }}
  .foot {{ color: var(--muted); font-size: 12px; margin-top: 16px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Watchlist &mdash; notas predichas</h1>
  <div class="sub">Generado el {generated} &middot; {n} t&iacute;tulos &middot;
    modelo: RandomForest sobre el desv&iacute;o vs IMDb (MAE &asymp; 1.26)</div>

  <div class="cards">
    <div class="card"><div class="n">{n}</div><div class="l">t&iacute;tulos</div></div>
    <div class="card"><div class="n">{mean_pred}</div><div class="l">nota predicha media</div></div>
    <div class="card"><div class="n">{n_ge7}</div><div class="l">con nota predicha &ge; 7</div></div>
    <div class="card"><div class="n">{n_lt5}</div><div class="l">con nota predicha &lt; 5</div></div>
  </div>

  <div id="chart"></div>

  <input type="search" id="q" placeholder="Buscar por t&iacute;tulo, director o g&eacute;nero&hellip;">
  <div class="tablewrap"><table id="t"><thead><tr>
    <th data-k="Title">T&iacute;tulo</th>
    <th data-k="Year" class="num">A&ntilde;o</th>
    <th data-k="Title Type">Tipo</th>
    <th data-k="IMDb Rating" class="num">IMDb</th>
    <th data-k="Directors">Director</th>
    <th data-k="pred_rating" class="num">Nota predicha</th>
    <th data-k="p_like" class="num">P(&ge;7)</th>
    <th data-k="Genres">G&eacute;neros</th>
  </tr></thead><tbody></tbody></table></div>

  <div class="foot">Tomar como <b>orden sugerido</b>, no como veredicto: el error
    t&iacute;pico es &plusmn;1.3 puntos. <code>pred_rating</code> y <code>p_like</code>
    salen de dos modelos distintos y pueden no coincidir.</div>
</div>

<script>
const DATA = {data_json};
let sortKey = "pred_rating", sortAsc = false;

function colorFor(v) {{
  const t = Math.max(0, Math.min(1, (v - 3) / 5));
  const hue = t * 120;               // 0=rojo, 120=verde
  return `hsl(${{hue}}, 62%, 42%)`;
}}

function render() {{
  const q = document.getElementById("q").value.trim().toLowerCase();
  let rows = DATA.filter(r => !q
    || r.Title.toLowerCase().includes(q)
    || (r.Genres || "").toLowerCase().includes(q)
    || (r.Directors || "").toLowerCase().includes(q));

  rows.sort((a, b) => {{
    let x = a[sortKey], y = b[sortKey];
    if (typeof x === "string") {{ x = x.toLowerCase(); y = (y || "").toLowerCase(); }}
    return (x < y ? -1 : x > y ? 1 : 0) * (sortAsc ? 1 : -1);
  }});

  const tb = document.querySelector("#t tbody");
  tb.innerHTML = rows.map(r => `
    <tr>
      <td>${{r.Title}}</td>
      <td class="num">${{r.Year ?? ""}}</td>
      <td>${{r["Title Type"]}}</td>
      <td class="num">${{r["IMDb Rating"] ?? ""}}</td>
      <td class="genres">${{r.Directors ?? ""}}</td>
      <td class="num"><span class="pill" style="background:${{colorFor(r.pred_rating)}}">${{r.pred_rating.toFixed(1)}}</span></td>
      <td class="num">${{(r.p_like * 100).toFixed(0)}}%</td>
      <td class="genres">${{r.Genres ?? ""}}</td>
    </tr>`).join("");

  document.querySelectorAll("#t th").forEach(th => {{
    th.classList.remove("sorted", "asc");
    if (th.dataset.k === sortKey) th.classList.add(sortAsc ? "asc" : "sorted");
  }});

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

document.querySelectorAll("#t th").forEach(th => th.addEventListener("click", () => {{
  const k = th.dataset.k;
  if (k === sortKey) sortAsc = !sortAsc;
  else {{ sortKey = k; sortAsc = false; }}
  render();
}}));
document.getElementById("q").addEventListener("input", render);
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
    html = TEMPLATE.format(
        generated=date.today().isoformat(),
        n=len(df),
        mean_pred=round(df["pred_rating"].mean(), 1),
        n_ge7=int((df["pred_rating"] >= 7).sum()),
        n_lt5=int((df["pred_rating"] < 5).sum()),
        data_json=json.dumps(json.loads(df.to_json(orient="records")), ensure_ascii=False),
    )
    for dest in DESTS:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        print(f"Dashboard: {dest}")
    (DOCS / ".nojekyll").touch()
    print("Local: abrir con doble clic. Pages: 'make publish' actualiza el sitio.")


if __name__ == "__main__":
    build_html()
