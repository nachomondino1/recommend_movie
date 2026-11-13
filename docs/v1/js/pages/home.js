// Página de inicio: hero + los 2 pasos de IMDb (descargar y arrastrar los archivos).
// Las plataformas se eligen en "Qué ver". Requiere shared.js, csv.js, catalog.js y storage.js.

function setMsg(text, isError) {
  $("uploadMsg").textContent = text;
  $("uploadMsg").className = "msg" + (isError ? " msg--error" : "");
}

// Con datos ya cargados: un aviso en los pasos dice que no hace falta volver a cargarlos.
function updateLoadedState() {
  const data = loadData();
  const loaded = data.ratings.length > 0;
  // El CTA siempre lleva a los pasos: primero se cargan los datos; con datos ya cargados, ahí mismo está el botón a las recomendaciones
  $("heroCta").textContent = loaded ? "Ver mi carga" : "Empezar";
  $("loadedBanner").hidden = !loaded;
  if (loaded) {
    const when = data.savedAt ? ` el ${new Date(data.savedAt).toLocaleDateString("es-AR")}` : "";
    $("loadedText").textContent = `${data.ratings.length} notas y ${data.watchlist.length} títulos en tu watchlist, cargados${when}. ` +
      "No hace falta volver a cargarlos: hacelo solo si agregaste notas nuevas en IMDb.";
  }
}

async function ingest(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  $("uploadDone").hidden = true;
  setMsg("Leyendo archivos…");
  const results = await readImdbFiles(files);
  const data = loadData();
  const notes = [];
  for (const r of results) {
    if (!r.kind || !r.rows.length) notes.push(`"${r.name}" no parece un archivo de IMDb.`);
    else data[r.kind] = r.rows;
  }
  if (!data.ratings.length) {
    setMsg(notes.concat("Falta el archivo de tus notas (ratings.csv).").join(" "), true);
    return;
  }
  data.savedAt = new Date().toISOString();
  if (!saveData(data)) {
    setMsg("No pude guardar tus datos en este navegador (¿ventana privada?).", true);
    return;
  }
  setMsg(notes.join(" "), notes.length > 0);
  showDone(data);
}

// Avisa que ya está todo cargado y ofrece ir a las recomendaciones (no redirige solo).
function showDone(data) {
  $("uploadDoneText").textContent = `Cargamos ${data.ratings.length} notas y ${data.watchlist.length} títulos de tu watchlist.` +
    (data.watchlist.length ? "" : " Todavía falta tu watchlist (es opcional): con ella te marcamos lo que ya guardaste.");
  $("uploadDone").hidden = false;
  updateLoadedState();   // primero se actualiza el layout (aparece el cuadro de arriba) y después se scrollea
  renderHeader("inicio");  // el menú ahora incluye Qué ver y Mis puntuaciones
  if (catalog.data) showCatalogInfo();
  $("uploadDone").scrollIntoView({ block: "center", behavior: reducedMotion() ? "auto" : "smooth" });
}

function wireUpload() {
  const zone = $("dropzone"), input = $("fileInput");
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => { ingest(input.files); input.value = ""; });
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("dropzone--over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("dropzone--over"); }));
  zone.addEventListener("drop", (e) => ingest(e.dataTransfer.files));
}

renderSite("inicio");
wireUpload();
updateLoadedState();
// El catálogo (2,5 MB) no frena la portada: se baja cuando el navegador está libre, para llenar el dato del pie
// y dejarlo en la caché HTTP para "Qué ver".
const warmCatalog = () => loadCatalog().catch(() => {});
if ("requestIdleCallback" in window) requestIdleCallback(warmCatalog, { timeout: 3000 }); else setTimeout(warmCatalog, 1500);
