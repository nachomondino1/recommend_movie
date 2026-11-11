// Página de inicio: hero + los 3 pasos (plataformas, descarga de IMDb, carga de archivos).
// Al guardar los datos lleva a "Qué ver". Requiere shared.js, csv.js, catalog.js y storage.js.

const selected = new Set(loadPlatforms().map((p) => p.id));

function setMsg(text, isError) {
  $("uploadMsg").textContent = text;
  $("uploadMsg").className = "msg" + (isError ? " msg--error" : "");
}

function persistPlatforms() {
  savePlatforms(catalog.data.providers.filter((p) => selected.has(p.id)).map((p) => ({ id: p.id, name: p.name })));
}

function renderProviders(list, onToggle) {
  $("providers").innerHTML = list.map((p) => `
    <button type="button" class="prov${selected.has(p.id) ? " prov--on" : ""}" data-id="${p.id}"
      aria-pressed="${selected.has(p.id)}">
      ${p.logo ? `<img src="${IMG}w92${p.logo}" alt="" loading="lazy">` : ""}
      <span>${esc(p.name)}</span>
    </button>`).join("");
  $("providers").querySelectorAll(".prov").forEach((b) => b.addEventListener("click", () => {
    const id = Number(b.dataset.id);
    onToggle(id);
    b.classList.toggle("prov--on", selected.has(id));
    b.setAttribute("aria-pressed", selected.has(id));
  }));
}

// Con datos ya cargados: el hero lleva directo a las recomendaciones, un aviso lo dice y los pasos 2 y 3
// quedan plegados para que nadie vuelva a cargar lo que ya está.
function updateLoadedState() {
  const data = loadData();
  const loaded = data.ratings.length > 0;
  const ready = loaded && selected.size > 0;
  $("heroCta").textContent = ready ? "Ver mis recomendaciones" : "Empezar";
  $("heroCta").setAttribute("href", ready ? "que-ver.html" : "#pasos");
  $("loadedBanner").hidden = !loaded;
  $("updateData").open = !loaded;
  $("updateData").classList.toggle("update--static", !loaded);
  if (loaded) {
    const when = data.savedAt ? ` el ${new Date(data.savedAt).toLocaleDateString("es-AR")}` : "";
    $("loadedText").textContent = `${data.ratings.length} notas y ${data.watchlist.length} títulos en tu watchlist, cargados${when}. ` +
      "No hace falta volver a cargarlos: hacelo solo si agregaste notas nuevas en IMDb.";
  }
}

async function ingest(fileList) {
  const files = [...fileList];
  if (!files.length) return;
  if (!selected.size) { setMsg("Primero elegí al menos una plataforma (paso 1).", true); return; }
  persistPlatforms();
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
  location.href = "que-ver.html";
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

async function main() {
  renderSite("inicio");
  wireUpload();
  updateLoadedState();
  try {
    await loadCatalog();
  } catch (e) {
    $("providers").innerHTML = `<div class="msg msg--error">${esc(e.message)}</div>`;
    return;
  }
  renderProviders(catalog.data.providers, (id) => {
    selected.has(id) ? selected.delete(id) : selected.add(id);
    persistPlatforms();
    updateLoadedState();
  });
}

main();
