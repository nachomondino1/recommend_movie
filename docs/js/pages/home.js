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

// Con datos ya cargados, el botón del hero lleva directo a las recomendaciones.
function updateHeroAndContinue() {
  const ready = loadData().ratings.length > 0 && selected.size > 0;
  $("heroCta").textContent = ready ? "Ver mis recomendaciones" : "Empezar";
  $("heroCta").setAttribute("href", ready ? "que-ver.html" : "#pasos");
  $("btnContinue").hidden = !loadData().ratings.length;
  $("btnContinue").disabled = !selected.size;
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
  $("btnContinue").addEventListener("click", () => { persistPlatforms(); location.href = "que-ver.html"; });
}

async function main() {
  renderSite("datos");
  wireUpload();
  updateHeroAndContinue();
  try {
    await loadCatalog();
  } catch (e) {
    $("providers").innerHTML = `<div class="msg msg--error">${esc(e.message)}</div>`;
    return;
  }
  renderProviders(catalog.data.providers, (id) => {
    selected.has(id) ? selected.delete(id) : selected.add(id);
    persistPlatforms();
    updateHeroAndContinue();
  });
}

main();
