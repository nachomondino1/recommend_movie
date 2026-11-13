// Helpers y componentes compartidos por las tres páginas (index, que-ver, mi-gusto).
// Requiere storage.js cargado antes. El encabezado y el pie se escriben UNA vez, acá (renderSite).

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const IMG = "https://image.tmdb.org/t/p/";
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const GENRE_ES = {
  Action: "Acción", Adventure: "Aventura", Animation: "Animación", Biography: "Biografía",
  Comedy: "Comedia", Crime: "Crimen", Documentary: "Documental", Drama: "Drama", Family: "Familia",
  Fantasy: "Fantasía", History: "Historia", Horror: "Terror", Music: "Música", Musical: "Musical",
  Mystery: "Misterio", Romance: "Romance", "Sci-Fi": "Ciencia ficción", Sport: "Deportes",
  Thriller: "Suspenso", War: "Bélica", Western: "Western", "Reality-TV": "Reality",
};
const genreEs = (g) => GENRE_ES[g] || g;
const typeLabel = (r) => (r.Type === "Movie" ? "Película" : "Serie");

function colorFor(v) {
  const t = Math.max(0, Math.min(1, (v - 3) / 5));
  return `hsl(${t * 120}, 40%, 33%)`;
}

function poster(r, size, cls) {
  return r.poster_path
    ? `<img class="${cls}" src="${IMG}${size}${r.poster_path}" alt="" loading="lazy">`
    : `<div class="${cls}"></div>`;
}

// ¿Ya cargó sus archivos? (entonces se habilitan Qué ver y Mis puntuaciones; las plataformas se eligen en Qué ver)
const hasProfile = () => loadData().ratings.length > 0;

// Para sumar una página: agregar una fila acá y crear su .html con <header id="siteHeader"> y <footer id="siteFooter">.
const NAV = [
  { id: "inicio", href: "index.html", label: "Inicio", needsProfile: false },
  { id: "que-ver", href: "que-ver.html", label: "Qué ver", needsProfile: false },
  { id: "mi-gusto", href: "mi-gusto.html", label: "Mis puntuaciones", needsProfile: false },
];

function syncNavHeight() {
  document.documentElement.style.setProperty("--nav-h", document.querySelector(".top").offsetHeight + "px");
}

// Pestañas de versión: el mismo selector en las tres versiones del sitio (V1, V2 y V3 = la actual, en la raíz).
// Los enlaces son relativos: desde /v1/ o /v2/ se sube un nivel; desde la raíz se baja.
function versionTabs() {
  const here = /\/v([123])\//.exec(location.pathname);
  const current = here ? Number(here[1]) : 0, up = here ? "../" : "";     // 0 = la landing, en la raíz
  const tabs = [[1, `${up}v1/index.html`, "«Qué ver hoy»"], [2, `${up}v2/index.html`, "«Tu número»"], [3, `${up}v3/index.html`, "la actual"]];
  return `<nav class="vtabs" aria-label="Versiones del proyecto">${tabs.map(([n, href, name]) =>
    `<a href="${href}" title="Versión ${n}, ${name}"${n === current ? ' aria-current="true"' : ""} data-track="version/v${n}"><span class="vlong">Versión</span><span class="vshort">V</span><span>${n}</span></a>`).join("")}</nav>`;
}

// El encabezado se dibuja ANTES del primer pintado: cada página llama renderHeader("<id>") en un <script> sincrónico
// justo debajo de <header id="siteHeader">, así el menú no aparece tarde ni empuja el contenido.
function renderHeader(active) {
  const profile = hasProfile();
  const items = NAV.filter((n) => !n.needsProfile || profile);
  const up = /\/v[123]\//.test(location.pathname) ? "../" : "";
  $("siteHeader").className = "top";
  // Barra principal: igual en las tres versiones. Subbarra: las pestañas de ESTA versión (solo si tiene más de una).
  $("siteHeader").innerHTML = `
    <div class="top-inner">
      <a class="brand" href="${up}index.html" aria-label="Recomendador de películas y series, inicio">&#127916;<span class="brand-text"> Recomendador de pel&iacute;culas y series</span></a>
      ${versionTabs()}
      <nav class="top-nav" aria-label="Enlaces">
        <a href="https://github.com/nachomondino1/recommend_movie" target="_blank" rel="noopener">C&oacute;digo &#8599;</a>
      </nav>
    </div>
    ${items.length > 1 ? `<nav class="subnav" aria-label="Páginas de esta versión"><div class="subnav-inner">${items.map((n) =>
      `<a href="${n.href}"${n.id === active ? ' aria-current="page"' : ""}>${esc(n.label)}</a>`).join("")}</div></nav>` : ""}`;
  syncNavHeight();
}

// Pie de página (y encabezado, si la página no lo dibujó antes). Se llama una vez por página.
function renderSite(active) {
  if (!$("siteHeader").firstElementChild) renderHeader(active);
  $("siteFooter").className = "foot";
  $("siteFooter").innerHTML = `
    <div class="wrap">
      <p class="note">Datos de pel&iacute;culas y series: <a href="https://www.themoviedb.org" target="_blank" rel="noopener">TMDB</a>.
        Este sitio no est&aacute; afiliado a IMDb ni a TMDB.</p>
      <p class="note" id="catalogInfo"></p>
      <p class="note"><button type="button" class="link-btn" id="btnClear">Borrar mis datos de este navegador</button></p>
    </div>`;
  $("btnClear").addEventListener("click", () => {
    if (!confirm("¿Borrar tus datos de este navegador?")) return;
    clearAllData();
    location.href = "index.html";
  });
  syncNavHeight();
}
window.addEventListener("resize", () => { if (document.querySelector(".top")) syncNavHeight(); });
