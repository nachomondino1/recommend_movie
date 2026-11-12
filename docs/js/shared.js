// Helpers y componentes compartidos por las tres páginas (index, numero, predecir).
// Requiere storage.js cargado antes. El encabezado y el pie se escriben UNA vez, acá (renderSite).

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const IMG = "https://image.tmdb.org/t/p/";
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Números con coma decimal (es-AR); signed() agrega el + a los positivos.
const fmtNum = (n, d = 1) => Number(n).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d });
const signed = (n, d = 1) => (n > 0 ? "+" : n < 0 ? "−" : "") + fmtNum(Math.abs(n), d);

function colorFor(v) {
  const t = Math.max(0, Math.min(1, (v - 3) / 5));
  return `hsl(${t * 120}, 40%, 33%)`;
}

// ¿Ya cargó sus archivos? (para mostrar tu número y las predicciones)
const hasProfile = () => loadData().ratings.length > 0;

// Para sumar una página: agregar una fila acá y crear su .html con <header id="siteHeader"> y <footer id="siteFooter">.
// index.html es la portada (el proyecto: flujo y resultados); numero.html junta cargar datos, tu número y predecir.
const NAV = [
  { id: "proyecto", href: "index.html", label: "Proyecto", needsProfile: false },
  { id: "numero", href: "numero.html", label: "Mi número", needsProfile: false },
];

function syncNavHeight() {
  document.documentElement.style.setProperty("--nav-h", document.querySelector(".top").offsetHeight + "px");
}

// El encabezado se dibuja ANTES del primer pintado: cada página llama renderHeader("<id>") en un <script> sincrónico
// justo debajo de <header id="siteHeader">, así el menú no aparece tarde ni empuja el contenido.
function renderHeader(active) {
  const profile = hasProfile();
  $("siteHeader").className = "top";
  $("siteHeader").innerHTML = `
    <div class="top-inner">
      <a class="brand" href="index.html" aria-label="Tu número, inicio">&#127916;<span class="brand-text"> Tu n&uacute;mero</span></a>
      <nav class="top-nav" aria-label="Secciones">
        ${NAV.filter((n) => !n.needsProfile || profile).map((n) =>
          `<a href="${n.href}"${n.id === active ? ' aria-current="page"' : ""}>${esc(n.label)}</a>`).join("")}
      </nav>
    </div>`;
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
