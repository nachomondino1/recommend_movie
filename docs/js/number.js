// "Tu número": cuánto te desviás, en promedio, de la nota de IMDb (tu nota − nota de IMDb), y la nota predicha
// para cualquier película = nota de IMDb + tu número. Es la regla más simple, y en las pruebas del repo
// (04_evaluation/robustness.py) ningún modelo más complejo la mejoró con evidencia suficiente.

const MIN_RATINGS = 10;   // con menos notas el promedio es demasiado inestable

// ratings: filas normalizadas del export de IMDb (YourRating, ImdbRating, Title, Year, URL, Runtime...).
// Devuelve null si no hay notas suficientes.
function computeNumber(ratings) {
  const rows = ratings.filter((r) => r.YourRating != null && r.ImdbRating != null)
    .map((r) => ({ ...r, dev: r.YourRating - r.ImdbRating }));
  const n = rows.length;
  if (n < MIN_RATINGS) return { n, enough: false };
  const devs = rows.map((r) => r.dev);
  const sum = devs.reduce((a, b) => a + b, 0);
  const mean = sum / n;
  const sorted = [...devs].sort((a, b) => a - b);
  const median = n % 2 ? sorted[(n - 1) / 2] : (sorted[n / 2 - 1] + sorted[n / 2]) / 2;
  const sd = Math.sqrt(devs.reduce((a, d) => a + (d - mean) ** 2, 0) / n);
  // Error típico de USAR el número para predecir: para cada título, se predice con el número calculado sin él
  const errs = devs.map((d) => Math.abs(d - (sum - d) / (n - 1)));
  return {
    n, enough: true, rows, mean, median, sd,
    mae: errs.reduce((a, b) => a + b, 0) / n,
    within1: errs.filter((e) => e <= 1).length / n,
    within2: errs.filter((e) => e <= 2).length / n,
  };
}

const predictRating = (imdb, number) => Math.min(10, Math.max(1, imdb + number));
