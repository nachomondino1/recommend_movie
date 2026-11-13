// Parseo de los exports de IMDb y detección de cuál es cuál por sus columnas.
// Requiere PapaParse (CDN) cargado antes.

function parseCsvFile(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => resolve(res),
      error: reject,
    });
  });
}

function detectKind(fields) {
  const f = new Set(fields || []);
  if (!f.has("Const") || !f.has("Title")) return null;
  if (f.has("Position")) return "watchlist";
  if (f.has("Your Rating")) return "ratings";
  return null;
}

function num(v) {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

function normalizeRow(r) {
  return {
    Const: (r["Const"] || "").trim(),
    Title: r["Title"] || "",
    Type: r["Title Type"] || "",
    Year: num(r["Year"]),
    Genres: r["Genres"] || "",
    Directors: r["Directors"] || "",
    ImdbRating: num(r["IMDb Rating"]),
    NumVotes: num(r["Num Votes"]),
    Runtime: num(r["Runtime (mins)"]),
    URL: r["URL"] || "",
    YourRating: num(r["Your Rating"]),
  };
}

// Devuelve [{kind, rows}] por archivo; kind es null si no es un export de IMDb.
async function readImdbFiles(files) {
  const out = [];
  for (const file of files) {
    try {
      const res = await parseCsvFile(file);
      const kind = detectKind(res.meta.fields);
      const rows = kind ? res.data.map(normalizeRow).filter((r) => r.Const) : [];
      out.push({ name: file.name, kind, rows });
    } catch (e) {
      out.push({ name: file.name, kind: null, rows: [] });
    }
  }
  return out;
}
