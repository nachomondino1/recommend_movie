// Encabezado y pie compartidos. Se escriben UNA vez, acá: la página llama renderHeader() en un <script> sincrónico
// justo debajo de <header id="siteHeader"> (así el menú no aparece tarde ni empuja el contenido) y renderSite() al final.

const $ = (id) => document.getElementById(id);
const REPO = "https://github.com/nachomondino1/recommend_movie";

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
      <p class="note">Datos de pel&iacute;culas y series: <a href="https://www.themoviedb.org" target="_blank" rel="noopener">TMDB</a>.
        Este producto usa la API de TMDB pero no est&aacute; avalado ni certificado por TMDB.</p>
    </div>`;
  syncNavHeight();
}
window.addEventListener("resize", () => { if (document.querySelector(".top")) syncNavHeight(); });
