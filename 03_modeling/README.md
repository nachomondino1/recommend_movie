# Fase 3 — Modelado

**El MVP público no modela ni predice nada.** Con ~100 notas por persona no hay datos suficientes (en el proyecto
personal, con 127 notas, el mejor modelo apenas mejoró la regla "IMDb menos 1.3 puntos") y un modelo por visitante
exigiría un backend. Tampoco hay un puntaje "para vos": inventar un número personalizado con tan poca información
sería ruido.

Lo que hace el sitio (`docs/js/app.js`), todo en el navegador y explicable:

1. Toma los títulos de tu watchlist y los del catálogo que **están en tus plataformas**.
2. **Descarta lo que ya viste** (por id de IMDb).
3. Los **ordena por la nota ponderada por votos**, como el Top 250 de IMDb: `rank = v/(v+m)·nota + m/(v+m)·7`
   (`v` = votos, `7` = nota neutra de referencia). Una nota alta con pocos votos se acerca a 7 y baja en la lista. `m` depende de
   la fuente porque las escalas son muy distintas: **25.000** para IMDb (tu watchlist; mediana ~210 mil votos) y **1.000** para TMDB
   (los nuevos; mediana ~600 votos, y se exige un mínimo de 500). La nota que se muestra es la cruda; el orden usa la ponderada.
4. Marca con "De tus géneros favoritos" los títulos de tus 3 géneros mejor puntuados (descriptivo; no cambia el orden).
5. **Directores favoritos**: un director con al menos 2 títulos tuyos y promedio por encima de tu nota media (hasta 3). Sus títulos se marcan
   con "De tus directores favoritos" y **suben 0,4 puntos** en el orden (`DIRECTOR_BOOST` en `docs/js/profile.js`), y los de la lista de
   nuevos entran aunque queden fuera de los 60 mejores. Es un impulso chico y fijo, no una predicción: con 2 títulos por director hay
   poca evidencia, así que solo desempata entre títulos de nota parecida.

El análisis de gusto (`docs/js/taste.js`) es solo estadística descriptiva de tus notas: promedios por género y
director, y cuánto te separás de la nota de IMDb.

El modelo entrenado del proyecto personal (RandomForest sobre el desvío vs. IMDb, `03_modeling/model.py`) sigue en este
mismo directorio y se documenta en `docs/4_modeling.md`.
