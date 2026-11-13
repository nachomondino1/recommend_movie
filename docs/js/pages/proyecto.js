// Portada "Proyecto" (flujo y resultados en una sola página de scroll): los gráficos de resultados, dibujados en SVG a mano
// con los números de data/model_results.json (los genera `make results` a partir de `make robust`).
// Requiere shared.js (renderSite).

(async function () {
  renderSite("proyecto");
  let DATA;
  try { DATA = await (await fetch("data/model_results.json")).json(); }
  catch (e) { DATA = null; }

const fmt = (n, d = 2) => Number(n).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (n, d = 3) => (n > 0 ? "+" : n < 0 ? "−" : "") + fmt(Math.abs(n), d);
const parseCI = (s) => s.replace(/[\[\]\s]/g, "").split(",").map(Number);
const ciEs = (s) => { const [a, b] = parseCI(s); return `[${sgn(a)}; ${sgn(b)}]`; };
const BASE = "IMDb calibrada (BASE)";
const rows = DATA ? DATA.comp : [];
                       // sin la fila de la base: no trae ΔMAE
const base = rows.find((r) => r.modelo === BASE);
const models = rows.filter((r) => r.modelo !== BASE);

// ---------- resumen ----------
const best = models.reduce((a, b) => (a["ΔMAE vs BASE"] < b["ΔMAE vs BASE"] ? a : b));
document.getElementById("s-base").textContent = fmt(base.MAE);
document.getElementById("s-best").textContent = sgn(best["ΔMAE vs BASE"], 2);
document.getElementById("s-best-l").textContent = `diferencia del mejor modelo (${best.modelo.replace(/ \(.*\)/, "")}), con IC95 ${ciEs(best["IC95 ΔMAE"])}`;

// ---------- gráfico de intervalos ----------
(function forest() {
  const W = 760, rowH = 38, m = { l: 250, r: 24, t: 12, b: 40 };
  const H = m.t + m.b + rowH * models.length;
  const lo = -0.2, hi = 0.64;
  const x = (v) => m.l + ((v - lo) / (hi - lo)) * (W - m.l - m.r);
  const ticks = [-0.2, 0, 0.2, 0.4, 0.6];
  let s = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
  ticks.forEach((t) => { s += `<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${m.t}" y2="${H - m.b}"/><text x="${x(t)}" y="${H - m.b + 18}" text-anchor="middle">${t > 0 ? "+" : t < 0 ? "−" : ""}${fmt(Math.abs(t), 1)}</text>`; });
  s += `<line class="zero" x1="${x(0)}" x2="${x(0)}" y1="${m.t}" y2="${H - m.b}"/>`;
  s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 4}" text-anchor="middle">Diferencia de error medio contra IMDb calibrada (puntos)</text>`;
  models.forEach((r, i) => {
    const y = m.t + i * rowH + rowH / 2, [a, b] = parseCI(r["IC95 ΔMAE"]), d = r["ΔMAE vs BASE"];
    s += `<text class="lab" x="${m.l - 14}" y="${y + 4}" text-anchor="end">${r.modelo.replace(/ \(.*\)/, "")}</text>`;
    s += `<line x1="${x(a)}" x2="${x(b)}" y1="${y}" y2="${y}" stroke="var(--accent)" stroke-width="3.5" stroke-linecap="round"/>`;
    s += `<circle cx="${x(d)}" cy="${y}" r="5.5" fill="var(--surface)" stroke="var(--accent)" stroke-width="2.5"/>`;
  });
  s += "</svg>";
  document.getElementById("forest").innerHTML = s;
})();

// ---------- tabla ----------
(function table() {
  const head = ["Modelo", "MAE", "RMSE", "±1", "Spearman", "AUC", "ΔMAE vs IMDb", "IC 95 %"];
  let h = `<tr>${head.map((x) => `<th>${x}</th>`).join("")}</tr>`;
  const order = [BASE, ...models.map((m) => m.modelo)];
  order.forEach((name) => {
    const r = rows.find((x) => x.modelo === name), isBase = name === BASE;
    h += `<tr class="${isBase ? "base" : ""}"><td>${name.replace(" (BASE)", "")}${isBase ? '<span class="pill">base</span>' : ""}</td>
      <td>${fmt(r.MAE, 3)}</td><td>${fmt(r.RMSE, 3)}</td><td>${fmt(r["±1"] * 100, 0)} %</td><td>${fmt(r.Spearman, 2)}</td><td>${fmt(r["AUC(>=7)"], 3)}</td>
      <td>${isBase ? "—" : sgn(r["ΔMAE vs BASE"])}</td><td>${isBase ? "—" : ciEs(r["IC95 ΔMAE"])}</td></tr>`;
  });
  document.getElementById("tbl").innerHTML = h;
})();

// ---------- curva de aprendizaje ----------
(function curve() {
  const series = [["IMDb calibrada", "IMDb calibrada (base)", "var(--muted)"], ["Ridge simple", "Ridge simple", "var(--warn)"], ["RandomForest", "RandomForest", "var(--accent)"]];
  const W = 760, H = 340, m = { l: 52, r: 24, t: 14, b: 44 };
  const sizes = DATA.lc["IMDb calibrada"].sizes, lo = 1.2, hi = 1.56;
  const x = (v) => m.l + ((v - 30) / 70) * (W - m.l - m.r);
  const y = (v) => H - m.b - ((v - lo) / (hi - lo)) * (H - m.t - m.b);
  let s = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
  [1.2, 1.3, 1.4, 1.5].forEach((t) => { s += `<line class="grid" x1="${m.l}" x2="${W - m.r}" y1="${y(t)}" y2="${y(t)}"/><text x="${m.l - 8}" y="${y(t) + 4}" text-anchor="end">${fmt(t, 1)}</text>`; });
  sizes.forEach((t) => { s += `<text x="${x(t)}" y="${H - m.b + 18}" text-anchor="middle">${t}</text>`; });
  s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 4}" text-anchor="middle">Títulos usados para entrenar</text>`;
  s += `<text transform="rotate(-90 14 ${(H - m.b + m.t) / 2})" x="14" y="${(H - m.b + m.t) / 2}" text-anchor="middle">Error medio en títulos no vistos</text>`;
  series.forEach(([key, , color]) => {
    const d = DATA.lc[key];
    const up = d.sizes.map((t, i) => `${x(t)},${y(d.mean[i] + d.se[i])}`);
    const dn = d.sizes.map((t, i) => `${x(t)},${y(d.mean[i] - d.se[i])}`).reverse();
    s += `<polygon points="${up.concat(dn).join(" ")}" fill="${color}" opacity=".12"/>`;
    s += `<polyline points="${d.sizes.map((t, i) => `${x(t)},${y(d.mean[i])}`).join(" ")}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linejoin="round"/>`;
    d.sizes.forEach((t, i) => { s += `<circle cx="${x(t)}" cy="${y(d.mean[i])}" r="3.5" fill="var(--surface)" stroke="${color}" stroke-width="2"/>`; });
  });
  s += "</svg>";
  document.getElementById("lc").innerHTML = s;
  document.getElementById("lc-leg").innerHTML = series.map(([, label, color]) => `<span><i style="background:${color}"></i>${label}</span>`).join("");
})();

// ---------- Los datos (describir los datos) ----------
(function datos() {
  const D = DATA && DATA.data;
  if (!D) return;
  const r = D.response, es = (n, d = 0) => fmt(n, d);
  document.getElementById("d-rows").textContent = D.n_rows;
  document.getElementById("d-pred-n").textContent = D.n_predictors;

  // histograma de la variable respuesta
  const W = 520, H = 250, m = { l: 34, r: 8, t: 14, b: 34 }, max = Math.max(...r.counts), bw = (W - m.l - m.r) / 10;
  let s = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
  [0, Math.round(max / 2), max].forEach((t) => { const y = H - m.b - (t / max) * (H - m.t - m.b); s += `<line class="grid" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/><text x="${m.l - 6}" y="${y + 4}" text-anchor="end">${t}</text>`; });
  r.counts.forEach((c, i) => {
    const h = (c / max) * (H - m.t - m.b), x = m.l + i * bw + bw * 0.14, y = H - m.b - h;
    s += `<rect x="${x}" y="${y}" width="${bw * 0.72}" height="${Math.max(h, 1)}" rx="3" fill="${i + 1 >= 7 ? "var(--accent)" : "var(--line-strong)"}"/>`;
    if (c) s += `<text x="${x + bw * 0.36}" y="${y - 5}" text-anchor="middle">${c}</text>`;
    s += `<text x="${x + bw * 0.36}" y="${H - m.b + 18}" text-anchor="middle">${i + 1}</text>`;
  });
  s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 2}" text-anchor="middle">Tu nota</text></svg>`;
  document.getElementById("d-histo").innerHTML = s;
  document.getElementById("d-resp").innerHTML = `
    <li><b>Resumen</b><span>Promedio ${es(r.mean, 2)}, mediana ${es(r.median, 0)}, desvío estándar ${es(r.sd, 2)}. Se concentra entre 5 y 8.</span></li>
    <li><b>"Me gustó" (nota ≥ 7)</b><span>${r.liked} de ${D.n_rows} títulos (${es(r.liked / D.n_rows * 100, 0)} %). Es la respuesta de la clasificación, en azul en el gráfico.</span></li>
    <li><b>Desvío contra IMDb</b><span>Tu nota menos la de IMDb: promedio ${sgn(r.deviation.mean, 2)}, desvío estándar ${es(r.deviation.sd, 2)}, sobre ${r.deviation.n} títulos. Es la respuesta de la regresión.</span></li>`;

  // variables predictoras
  document.getElementById("d-pred").innerHTML = D.predictors.map((g) => `
    <div class="pgroup"><div class="label">${g.group}</div>
      <div class="table-wrap"><table class="plain"><tr><th>Variable</th><th>Qué es</th><th>Tipo</th></tr>
      ${g.vars.map((v) => `<tr><td><code>${v.names.join(", ")}</code></td><td>${v.what}</td><td>${v.kind}</td></tr>`).join("")}
      </table></div></div>`).join("");

  // calidad
  const names = { overview: "Sinopsis", keywords: "Palabras clave", cast_top: "Elenco", director: "Director o creador" };
  document.getElementById("d-quality").innerHTML = Object.entries(D.tmdb_coverage).map(([k, n]) => `
    <div class="qrow"><span>${names[k]}</span><span class="qbar"><i style="width:${n / D.tmdb_rows * 100}%"></i></span><b>${n} de ${D.tmdb_rows}</b></div>`).join("");
})();

// ---------- Solapas de la página: marca la sección que se está viendo ----------
(function spy() {
  // El alto real de la barra de solapas entra en el margen de scroll de cada sección, para que no tape el título al saltar
  const bar = document.querySelector(".secnav");
  if (bar) {
    const sync = () => bar.closest(".proy").style.setProperty("--subnav-h", bar.offsetHeight + "px");
    sync();
    window.addEventListener("resize", sync);
  }
  const links = [...document.querySelectorAll(".secnav a")];
  if (!links.length || !("IntersectionObserver" in window)) return;
  const byId = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { links.forEach((a) => a.removeAttribute("aria-current")); byId.get(e.target.id).setAttribute("aria-current", "true"); } });
  }, { rootMargin: "-30% 0px -60% 0px" });
  byId.forEach((_, id) => { const el = document.getElementById(id); if (el) io.observe(el); });
})();

// ---------- Ejemplo de la conclusión: cómo se usa el número ----------
(function ejemplo() {
  const D = DATA && DATA.data && DATA.data.response.deviation;
  if (!D) return;
  const IMDB = 7.5, num = D.mean, pred = Math.min(10, Math.max(1, IMDB + num));
  const lo1 = Math.max(1, pred - 1), hi1 = Math.min(10, pred + 1), lo2 = Math.max(1, pred - 2), hi2 = Math.min(10, pred + 2);
  const p1 = fmt(D.within1 * 100, 0), p2 = fmt(D.within2 * 100, 0);
  const he = document.getElementById("hero-eq");
  if (he) he.innerHTML = `
    <div class="heq"><b>${fmt(IMDB, 1)}</b><span>nota de IMDb</span></div><div class="hop">${num < 0 ? "−" : "+"}</div>
    <div class="heq"><b>${fmt(Math.abs(num), 1)}</b><span>mi número</span></div><div class="hop">=</div>
    <div class="heq res"><b>${fmt(pred, 1)}</b><span>mi nota estimada</span></div>`;
  document.getElementById("ex-eq").innerHTML = `
    <div class="eqn"><b>${fmt(IMDB, 1)}</b><span>nota de IMDb</span></div><div class="op">${num < 0 ? "−" : "+"}</div>
    <div class="eqn"><b>${fmt(Math.abs(num), 1)}</b><span>mi número</span></div><div class="op">=</div>
    <div class="eqn res"><b>${fmt(pred, 1)}</b><span>mi nota estimada</span></div>`;
  // escala del 1 al 10
  const W = 760, H = 150, m = { l: 20, r: 20 }, x = (v) => m.l + ((v - 1) / 9) * (W - m.l - m.r), y = 78;
  let s = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
  s += `<rect x="${x(lo2)}" y="${y - 20}" width="${x(hi2) - x(lo2)}" height="40" rx="8" fill="var(--accent)" opacity=".14"/>`;
  s += `<rect x="${x(lo1)}" y="${y - 20}" width="${x(hi1) - x(lo1)}" height="40" rx="8" fill="var(--accent)" opacity=".28"/>`;
  s += `<line x1="${x(1)}" x2="${x(10)}" y1="${y}" y2="${y}" stroke="var(--line-strong)" stroke-width="2"/>`;
  for (let v = 1; v <= 10; v++) s += `<line x1="${x(v)}" x2="${x(v)}" y1="${y - 5}" y2="${y + 5}" stroke="var(--line-strong)"/><text x="${x(v)}" y="${y + 38}" text-anchor="middle">${v}</text>`;
  s += `<path d="M ${x(IMDB)} ${y - 30} Q ${(x(IMDB) + x(pred)) / 2} ${y - 62} ${x(pred)} ${y - 30}" fill="none" stroke="var(--muted)" stroke-width="1.6" stroke-dasharray="4 3"/>`;
  s += `<text x="${(x(IMDB) + x(pred)) / 2}" y="${y - 52}" text-anchor="middle">${signed(num)}</text>`;
  s += `<circle cx="${x(IMDB)}" cy="${y}" r="8" fill="var(--surface)" stroke="var(--muted)" stroke-width="2.5"/><text class="lab" x="${x(IMDB)}" y="${y - 18}" text-anchor="middle">IMDb ${fmt(IMDB, 1)}</text>`;
  s += `<circle cx="${x(pred)}" cy="${y}" r="9" fill="var(--accent)"/><text class="lab lab-base" x="${x(pred)}" y="${y + 56}" text-anchor="middle">${fmt(pred, 1)}</text>`;
  s += "</svg>";
  document.getElementById("ex-scale").innerHTML = s;
  document.getElementById("ex-leg").innerHTML = `<span><i style="background:var(--accent);opacity:.3"></i>Entre ${fmt(lo1, 1)} y ${fmt(hi1, 1)}: ${p1} % de las veces</span><span><i style="background:var(--accent);opacity:.15"></i>Entre ${fmt(lo2, 1)} y ${fmt(hi2, 1)}: ${p2} % de las veces</span>`;
  document.getElementById("ex-text").innerHTML = `
    <li><b>Estimación: ${fmt(pred, 1)}</b><span>La nota de IMDb (${fmt(IMDB, 1)}) más mi número (${signed(num)}).</span></li>
    <li><b>Rango habitual: ${fmt(lo1, 1)} a ${fmt(hi1, 1)}</b><span>Mi nota real quedó a un punto o menos de la estimación el ${p1} % de las veces.</span></li>
    <li><b>Rango amplio: ${fmt(lo2, 1)} a ${fmt(hi2, 1)}</b><span>A dos puntos o menos el ${p2} % de las veces. Fuera de ese rango pasó el ${fmt(100 - D.within2 * 100, 0)} %.</span></li>
    <li><b>Error típico: ±${fmt(D.mae, 1)}</b><span>No es un número exacto. Es la mejor pista simple que encontré.</span></li>`;
})();

})();
