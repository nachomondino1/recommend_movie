// Persistencia local: dataset parseado + plataformas elegidas. Todo en el navegador.

const DATA_KEY = "mvp_data_v1", PLATFORMS_KEY = "mvp_platforms_v2";

function loadData() {
  try { return JSON.parse(localStorage.getItem(DATA_KEY)) || { ratings: [], watchlist: [] }; }
  catch (e) { return { ratings: [], watchlist: [] }; }
}

function saveData(data) {
  try { localStorage.setItem(DATA_KEY, JSON.stringify(data)); return true; }
  catch (e) { return false; }
}

function clearAllData() {
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith("mvp_"))
      .forEach((k) => localStorage.removeItem(k));
  } catch (e) { /* sin acceso a storage */ }
}

// [{id, name}]
function loadPlatforms() {
  try { return JSON.parse(localStorage.getItem(PLATFORMS_KEY) || "[]"); }
  catch (e) { return []; }
}

function savePlatforms(list) {
  try { localStorage.setItem(PLATFORMS_KEY, JSON.stringify(list)); } catch (e) { /* ignorar */ }
}
