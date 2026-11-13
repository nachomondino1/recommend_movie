// Catálogo de títulos en streaming (data/catalog.json, generado por 02_data_preparation/build_catalog.py).
// El sitio no llama a ninguna API: todo sale de este archivo.

const catalog = { data: null, byImdb: new Map(), providerName: new Map() };

function normTitle(s) {
  return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
}

async function loadCatalog() {
  const res = await fetch("../data/catalog.json");
  if (!res.ok) throw new Error("No encontré el catálogo (data/catalog.json).");
  catalog.data = await res.json();
  catalog.data.providers.forEach((p) => catalog.providerName.set(p.id, p.name));
  catalog.data.titles.forEach((t) => { if (t.imdb) catalog.byImdb.set(t.imdb, t); });
  showCatalogInfo();
  return catalog.data;
}

const providerNames = (ids) => ids.map((id) => catalog.providerName.get(id)).filter(Boolean);

// Disclaimer del pie: cuántos títulos tiene el catálogo y de cuándo es.
function showCatalogInfo() {
  const el = document.getElementById("catalogInfo");
  if (!el) return;
  const n = (x) => x.toLocaleString("es-AR");
  const total = catalog.data.titles.length, movies = catalog.data.titles.filter((t) => t.type === "movie").length;
  el.textContent = `Catálogo: ${n(total)} títulos (${n(movies)} películas y ${n(total - movies)} series) en ` +
    `${catalog.data.providers.length} plataformas de ${catalog.data.region}, actualizado el ${catalog.data.generated}.`;
}
