// Página "Mi número": tu desvío contra IMDb, qué tan confiable es y dos gráficos simples (SVG a mano, sin librerías).
// Requiere shared.js, number.js y storage.js.

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

function main() {
  renderSite("numero");
  const data = loadData();
  if (!data.ratings.length) { $("noData").hidden = false; return; }
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
}

main();
