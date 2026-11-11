// Página de inicio: hero + los 2 pasos de IMDb (descargar y arrastrar los archivos).
// Las plataformas se eligen en "Qué ver". Requiere shared.js, csv.js, catalog.js y storage.js.

function setMsg(text, isError) {
  $("uploadMsg").textContent = text;
  $("uploadMsg").className = "msg" + (isError ? " msg--error" : "");
}

// Con datos ya cargados: el hero lleva directo a las recomendaciones y un aviso dice que no hace falta volver a cargarlos.
function updateLoadedState() {
  const data = loadData();
  const loaded = data.ratings.length > 0;
  $("heroCta").textContent = loaded ? "Ver mis recomendaciones" : "Empezar";
  $("heroCta").setAttribute("href", loaded ? "que-ver.html" : "#pasos");
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
  renderSite("inicio");  // el menú ahora incluye Qué ver y Mi gusto
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
loadCatalog().catch(() => {});   // solo para llenar el dato del pie y dejar el catálogo en caché para "Qué ver"
