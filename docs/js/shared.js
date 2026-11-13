// Encabezado, pie, contacto y medición de visitas compartidos. Se escriben UNA vez, acá: la página llama renderHeader() en un <script> sincrónico
// justo debajo de <header id="siteHeader"> (así el menú no aparece tarde ni empuja el contenido) y renderSite() al final.

const $ = (id) => document.getElementById(id);
const REPO = "https://github.com/nachomondino1/recommend_movie";

// ---- Medición de visitas (GoatCounter, sin cookies). Solo se activa si SITE.goatcounter tiene un código. ----
function loadAnalytics() {
  if (!SITE.goatcounter || document.querySelector("script[data-goatcounter]")) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = "https://gc.zgo.at/count.js";
  s.dataset.goatcounter = `https://${SITE.goatcounter}.goatcounter.com/count`;
  document.head.appendChild(s);
}

// Cuenta un evento propio (un enlace tocado, una sección vista). Cada evento aparece en el panel como una "página" más,
// con el prefijo del tipo: p. ej. "enlace/codigo", "seccion/resultados", "version/v1". Si no hay medidor, no hace nada.
function track(name, title) {
  try {
    if (window.goatcounter && window.goatcounter.count) window.goatcounter.count({ path: name, title: title || name, event: true });
  } catch (e) { /* medir nunca debe romper la página */ }
}

// Cuenta una sola vez cada sección de la página cuando aparece en pantalla (para ver hasta dónde llega la gente).
function trackSections(ids) {
  if (!SITE.goatcounter || !("IntersectionObserver" in window)) return;
  const seen = new Set();
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    if (e.isIntersecting && !seen.has(e.target.id)) { seen.add(e.target.id); track(`seccion/${e.target.id}`, `Sección ${e.target.id}`); }
  }), { threshold: 0.25 });
  ids.forEach((id) => { const el = document.getElementById(id); if (el) io.observe(el); });
}

// ---- Contacto: solo aparecen los canales que tengan dato en js/config.js ----
function contactHtml(c) {
  const links = [];
  if (c.whatsapp) links.push(`<a class="contact-btn" data-track="contacto/whatsapp" target="_blank" rel="noopener" href="https://wa.me/${c.whatsapp}?text=${encodeURIComponent(c.whatsappText || "")}">WhatsApp</a>`);
  if (c.linkedin) links.push(`<a class="contact-btn" data-track="contacto/linkedin" target="_blank" rel="noopener" href="${c.linkedin}">LinkedIn</a>`);
  if (c.email) links.push(`<a class="contact-btn" data-track="contacto/email" href="mailto:${c.email}">${c.email}</a>`);
  return links.length ? `<div class="contact"><p class="contact-title">¿Querés comentarme algo?</p><div class="contact-links">${links.join("")}</div></div>` : "";
}

function syncNavHeight() {
  document.documentElement.style.setProperty("--nav-h", document.querySelector(".top").offsetHeight + "px");
}

function renderHeader() {
  $("siteHeader").className = "top";
  $("siteHeader").innerHTML = `
    <div class="top-inner">
      <a class="brand" href="index.html" aria-label="Qué hace buena a una película, inicio">&#127916;<span class="brand-text"> Qu&eacute; hace buena a una pel&iacute;cula</span></a>
      <nav class="top-nav" aria-label="Enlaces">
        <a href="${REPO}" target="_blank" rel="noopener">C&oacute;digo &#8599;</a>
      </nav>
    </div>`;
  syncNavHeight();
}

// Pie de página (y encabezado, si la página no lo dibujó antes). Se llama una vez por página.
function renderSite() {
  if (!$("siteHeader").firstElementChild) renderHeader();
  $("siteFooter").className = "foot";
  $("siteFooter").innerHTML = `
    <div class="wrap">
      ${contactHtml(SITE.contact)}
      <p class="note">Datos de pel&iacute;culas y series: <a href="https://www.themoviedb.org" target="_blank" rel="noopener">TMDB</a>.
        Este producto usa la API de TMDB pero no est&aacute; avalado ni certificado por TMDB.</p>
      ${SITE.goatcounter ? '<p class="note">Esta p&aacute;gina mide las visitas de forma an&oacute;nima, sin cookies, con <a href="https://www.goatcounter.com" target="_blank" rel="noopener">GoatCounter</a>.</p>' : ""}
    </div>`;
  // Los enlaces con data-track cuentan el toque como evento
  document.querySelectorAll("[data-track]").forEach((a) => a.addEventListener("click", () => track(a.dataset.track)));
  loadAnalytics();
  syncNavHeight();
}
window.addEventListener("resize", () => { if (document.querySelector(".top")) syncNavHeight(); });
