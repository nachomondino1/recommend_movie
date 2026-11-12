// Portada del proyecto "¿Qué hace que una película tenga buena nota?": una sola página de scroll.
// Todos los números salen de data/model_results.json (lo arma `make results` a partir de `make drivers`);
// el HTML trae los mismos valores escritos como respaldo por si el archivo no carga. Los gráficos son SVG a mano.
// Requiere shared.js (renderSite).

(async function () {
  renderSite("proyecto");
  let R = null;
  try { R = await (await fetch("data/model_results.json")).json(); } catch (e) { /* queda el texto de respaldo */ }
  const $id = (id) => document.getElementById(id);
  const fmt = (n, d = 2) => Number(n).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d });
  const sgn = (n, d = 2) => (n > 0 ? "+" : n < 0 ? "−" : "") + fmt(Math.abs(n), d);
  const M = R && R.drivers, D = R && R.data;

  // ---------- Barra de solapas: alto real para los anclajes + sección visible ----------
  (function nav() {
    const bar = document.querySelector(".secnav");
    if (!bar) return;
    const sync = () => bar.closest(".proy").style.setProperty("--subnav-h", bar.offsetHeight + "px");
    sync();
    window.addEventListener("resize", sync);
    const links = [...bar.querySelectorAll("a")];
    if (!("IntersectionObserver" in window)) return;
    const byId = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { links.forEach((a) => a.removeAttribute("aria-current")); byId.get(e.target.id).setAttribute("aria-current", "true"); } });
    }, { rootMargin: "-30% 0px -60% 0px" });
    byId.forEach((_, id) => { const el = $id(id); if (el) io.observe(el); });
  })();

  if (!M || !D) return;
  const perf = M.performance.contenido, sinCast = M.performance["sin elenco ni equipo"];
  const eff = (name) => (M.effects.find((e) => e.var === name) || {}).effect;
  const rob = (label) => M.robustness.find((r) => r.label === label);
  const by = D.rating.by_type;

  // ---------- Números del texto ----------
  const vals = {
    r2: fmt(perf.r2, 2), r2pct: fmt(perf.r2 * 100, 0), mae: fmt(perf.mae, 2), maeBase: fmt(perf.mae_base, 2),
    r2NoCast: sinCast ? fmt(sinCast.r2, 2) : "", docEff: fmt(Math.abs(eff("Documental") ?? 0), 1), terrorEff: fmt(Math.abs(eff("Terror") ?? 0), 1),
    durEff: fmt(eff("Cada hora más de duración") ?? 0, 1), dirEff: fmt(eff("Director con 3+ títulos en el catálogo") ?? 0, 1),
    tvMean: fmt(by.tv.mean, 1), movieMean: fmt(by.movie.mean, 1), tvR2: fmt((rob("Solo series") || {}).r2 ?? 0, 2),
  };
  document.querySelectorAll("[data-v]").forEach((el) => { if (vals[el.dataset.v]) el.textContent = vals[el.dataset.v]; });

  // ---------- Portada ----------
  $id("hero-stats").innerHTML = `
    <div class="heq"><b>${fmt(M.n, 0)}</b><span>títulos analizados</span></div>
    <div class="heq"><b>${fmt(perf.mae, 2)}</b><span>error medio del modelo, contra ${fmt(perf.mae_base, 2)} de predecir el promedio</span></div>
    <div class="heq res"><b>${fmt(perf.r2 * 100, 0)} %</b><span>de la variación de la nota se explica</span></div>`;
  $id("f-total").textContent = fmt(D.n_total, 0);
  $id("f-model").textContent = fmt(D.n_model, 0);

  // ---------- Lo que sube y lo que baja ----------
  const nm = (e) => (e.var === "Música" ? "Género música" : e.var);          // para no confundirlo con el compositor
  const sn = (n) => (n < 0 ? "−" : "") + fmt(Math.abs(n));
  const item = (e) => `<li><span>${nm(e)}</span><b>${sgn(e.effect)}</b><i>[${sn(e.lo)}; ${sn(e.hi)}]</i></li>`;
  const real = M.effects.filter((e) => e.var !== "Es serie (contra película)");
  $id("eff-up").innerHTML = real.filter((e) => e.lo > 0).sort((a, b) => b.effect - a.effect).slice(0, 6).map(item).join("");
  $id("eff-down").innerHTML = real.filter((e) => e.hi < 0).sort((a, b) => a.effect - b.effect).slice(0, 4).map(item).join("") +
    `<li class="aside"><span>Las series, en promedio</span><b>${sgn(eff("Es serie (contra película)") ?? 0)}</b><i>más que las películas (ver cuidados)</i></li>`;

  // ---------- Los datos ----------
  $id("d-rows").textContent = fmt(D.n_total, 0);
  $id("d-model").textContent = fmt(D.n_model, 0);
  const rt = D.rating, W = 560, H = 250, m = { l: 36, r: 8, t: 14, b: 38 }, max = Math.max(...rt.counts), bw = (W - m.l - m.r) / rt.counts.length;
  let s = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true">`;
  [0, Math.round(max / 2), max].forEach((t) => { const y = H - m.b - (t / max) * (H - m.t - m.b); s += `<line class="grid" x1="${m.l}" x2="${W - m.r}" y1="${y}" y2="${y}"/><text x="${m.l - 6}" y="${y + 4}" text-anchor="end">${t}</text>`; });
  rt.counts.forEach((c, i) => {
    const h = (c / max) * (H - m.t - m.b), x = m.l + i * bw + bw * 0.1, y = H - m.b - h;
    s += `<rect x="${x}" y="${y}" width="${bw * 0.8}" height="${Math.max(h, 1)}" rx="2" fill="${rt.bins[i] >= 7 ? "var(--accent)" : "var(--line-strong)"}"/>`;
    if (Number.isInteger(rt.bins[i])) s += `<text x="${x}" y="${H - m.b + 18}" text-anchor="middle">${rt.bins[i]}</text>`;
  });
  s += `<text x="${(m.l + W - m.r) / 2}" y="${H - 2}" text-anchor="middle">Nota de TMDB</text></svg>`;
  $id("d-histo").innerHTML = s;
  $id("d-resp").innerHTML = `
    <li><b>Resumen</b><span>Promedio ${fmt(rt.mean, 2)} y desvío estándar ${fmt(rt.sd, 2)}. Se concentra entre 6 y 8.</span></li>
    <li><b>Películas y series</b><span>Las películas promedian ${fmt(by.movie.mean, 2)} (desvío ${fmt(by.movie.sd, 2)}) y las series ${fmt(by.tv.mean, 2)} (desvío ${fmt(by.tv.sd, 2)}). Por eso conviene mirarlas por separado.</span></li>
    <li><b>Con nota de 7 o más</b><span>${fmt(rt.share_ge7 * 100, 0)} % de los títulos, en azul en el gráfico.</span></li>`;
  $id("d-pred").innerHTML = `<tr><th>Grupo</th><th>Variables</th><th>Qué es</th><th>Tipo</th></tr>` + D.predictors.map((g) =>
    g.vars.map((v, i) => `<tr><td>${i === 0 ? `<b>${g.group}</b>` : ""}</td><td><code>${v.names.join(", ")}</code></td><td>${v.what}</td><td>${v.kind}</td></tr>`).join("")).join("");
  $id("d-quality").innerHTML = Object.entries(D.coverage).map(([k, p]) => `
    <div class="qrow"><span>${k}</span><span class="qbar"><i style="width:${p * 100}%"></i></span><b>${fmt(p * 100, 0)} %</b></div>`).join("");

  // ---------- Los modelos ----------
  const series = rob("Solo series");
  $id("m-stats").innerHTML = [
    [fmt(M.n, 0), `películas y series con al menos ${fmt(M.min_votes, 0)} votos`, "drivers_results.json"],
    [fmt(perf.r2, 2), "R²: parte de la variación de la nota que se explica", "validación cruzada"],
    [`${fmt(perf.mae, 2)} contra ${fmt(perf.mae_base, 2)}`, "error medio contra predecir siempre el promedio", "validación cruzada"],
    [series ? fmt(series.r2, 2) : "—", "R² solo en series: casi no se predice", "prueba de robustez"],
  ].map(([b, l, src]) => `<div class="stat"><b>${b}</b><span>${l}</span><span class="src">${src}</span></div>`).join("");

  const ab = (g) => (M.importance.find((o) => o.group === g) || {}).ablation_drop;
  if (sinCast) {
    $id("m-cast").textContent = `Sumar elenco y equipo mejora poco: el R² pasa de ${fmt(sinCast.r2, 2)} a ${fmt(perf.r2, 2)}. ` +
      (ab("Elenco") > 0.01 ? "El elenco aporta información propia. " : "El elenco no aporta mucho por sí solo. ") +
      (ab("Guion, música y fotografía") <= 0.005 ? "El guion, la música y la fotografía no aportan nada que se distinga del ruido." : "El guion, la música y la fotografía aportan algo.");
  }

  // importancia por grupo
  const imp = M.importance, iw = 760, rowH = 46, im = { l: 210, r: 60, t: 8, b: 8 }, ih = im.t + im.b + rowH * imp.length;
  const mx = Math.max(...imp.map((o) => Math.max(o.perm_drop, o.ablation_drop))), ix = (v) => (v / mx) * (iw - im.l - im.r);
  let g = `<svg viewBox="0 0 ${iw} ${ih}" aria-hidden="true">`;
  imp.forEach((o, i) => {
    const y = im.t + i * rowH;
    g += `<text class="lab" x="${im.l - 12}" y="${y + 20}" text-anchor="end">${o.group}</text>`;
    g += `<rect x="${im.l}" y="${y + 6}" width="${Math.max(ix(o.perm_drop), 1)}" height="14" rx="3" fill="var(--accent)"/><text x="${im.l + ix(o.perm_drop) + 6}" y="${y + 18}">${fmt(o.perm_drop, 2)}</text>`;
    g += `<rect x="${im.l}" y="${y + 24}" width="${Math.max(ix(Math.max(o.ablation_drop, 0)), 1)}" height="10" rx="3" fill="var(--line-strong)"/><text x="${im.l + ix(Math.max(o.ablation_drop, 0)) + 6}" y="${y + 34}">${fmt(o.ablation_drop, 2)}</text>`;
  });
  $id("m-imp").innerHTML = g + "</svg>";

  // efectos ajustados
  const ef = [...M.effects].sort((a, b) => b.effect - a.effect), ew = 760, erow = 34, em = { l: 280, r: 56, t: 8, b: 40 };
  const eh = em.t + em.b + erow * ef.length, lo = -0.6, hi = 1.5, ex = (v) => em.l + ((v - lo) / (hi - lo)) * (ew - em.l - em.r);
  let e = `<svg viewBox="0 0 ${ew} ${eh}" aria-hidden="true">`;
  [-0.5, 0, 0.5, 1, 1.5].forEach((t) => { e += `<line class="grid" x1="${ex(t)}" x2="${ex(t)}" y1="${em.t}" y2="${eh - em.b}"/><text x="${ex(t)}" y="${eh - em.b + 18}" text-anchor="middle">${t > 0 ? "+" : t < 0 ? "−" : ""}${fmt(Math.abs(t), 1)}</text>`; });
  e += `<line class="zero" x1="${ex(0)}" x2="${ex(0)}" y1="${em.t}" y2="${eh - em.b}"/>`;
  e += `<text x="${(em.l + ew - em.r) / 2}" y="${eh - 4}" text-anchor="middle">Puntos de nota (TMDB)</text>`;
  ef.forEach((r, i) => {
    const y = em.t + i * erow + erow / 2;
    e += `<text class="lab" x="${em.l - 12}" y="${y + 4}" text-anchor="end">${nm(r)}</text>`;
    e += `<line x1="${ex(r.lo)}" x2="${ex(r.hi)}" y1="${y}" y2="${y}" stroke="var(--accent)" stroke-width="3.5" stroke-linecap="round"/>`;
    e += `<circle cx="${ex(r.effect)}" cy="${y}" r="5.5" fill="var(--surface)" stroke="var(--accent)" stroke-width="2.5"/>`;
    e += `<text x="${ex(r.hi) + 8}" y="${y + 4}">${sgn(r.effect, 2)}</text>`;
  });
  $id("m-eff").innerHTML = e + "</svg>";

  // actores
  if (M.actors) {
    $id("m-actors").hidden = false;
    $id("m-actors-sub").textContent = `Actores del elenco principal con al menos ${M.actors.min_titles} títulos en el catálogo (${fmt(M.actors.n_actors, 0)} actores). Se ordenan por cuánto mejor, o peor, es la nota de sus títulos de lo que se esperaría por formato, género, duración, año y plataformas.`;
    const rows = (list) => `<tr><th>Actor</th><th>Títulos</th><th>Diferencia</th></tr>` + list.map((a) => `<tr><td>${a.name}</td><td>${a.n}</td><td>${sgn(a.resid, 2)} ± ${fmt(1.96 * a.se, 2)}</td></tr>`).join("");
    $id("m-act-top").innerHTML = rows(M.actors.top);
    $id("m-act-bot").innerHTML = rows(M.actors.bottom);
  }

  // robustez
  $id("m-rob").innerHTML = `<tr><th>Recorte</th><th>Títulos</th><th>R²</th><th>Error medio</th></tr>` +
    [{ label: "Todo el catálogo (≥ 100 votos)", n: M.n, ...perf }, ...M.robustness].map((r) => `<tr><td>${r.label}</td><td>${fmt(r.n, 0)}</td><td>${fmt(r.r2, 2)}</td><td>${fmt(r.mae, 2)} (${fmt(r.mae_base, 2)})</td></tr>`).join("");
})();
