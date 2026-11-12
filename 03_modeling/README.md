# Fase 3 — Modelado

**El MVP público no modela ni predice nada.** Con ~100 notas por persona no hay datos suficientes (en el proyecto
personal, con 127 notas, el mejor modelo apenas mejoró la regla "IMDb menos 1.3 puntos") y un modelo por visitante
exigiría un backend. Tampoco hay un puntaje "para vos": inventar un número personalizado con tan poca información
sería ruido.

Lo que hace el sitio (`docs/js/profile.js` arma los datos y `docs/js/pages/que-ver.js` los muestra), todo en el navegador y explicable:

1. Parte de **todo el catálogo** (hoy ~5.100 títulos) y le suma lo tuyo que no esté ahí. Cada título sabe si está **en las plataformas que elegís** (lista desplegable con casillas en "Qué ver", se recuerdan entre visitas; sin ninguna elegida, todo el catálogo cuenta como disponible), si **ya lo
   viste** (por id de IMDb, con tu nota) y si está en tu **watchlist**.
2. Por defecto lista lo que está **en tus plataformas y todavía no viste**; con el **buscador por nombre** mira el catálogo entero (otras
   plataformas, lo ya visto, lo que no está en ninguna) e ignora los filtros.
3. **Nota y votos de todo el catálogo son de TMDB**, así son comparables entre sí; en los títulos de tu watchlist se muestra además la nota y los
   votos de IMDb. Los títulos fuera del catálogo (solo aparecen al buscar) usan los de IMDb.
4. **El orden lo elegís vos**: *Recomendado*, *Mejor nota*, *Más votos*, *Más nuevas* o *Nombre A–Z*, más un piso de **votos mínimos**
   (100 a 10.000) para combinar nota alta con muchos votantes a tu criterio.
5. **Recomendado** = nota ponderada por votos, como el Top 250 de IMDb: `rank = v/(v+m)·nota + m/(v+m)·7` (`v` = votos, `7` = nota neutra de
   referencia). Una nota alta con pocos votos se acerca a 7 y baja. `m` = **1.000** para TMDB (mediana ~600 votos) y **25.000** para IMDb
   (mediana ~210 mil). Se muestra la nota cruda; solo el orden usa la ponderada.
6. Marca con "De tus géneros favoritos" los títulos de tus 3 géneros mejor puntuados (descriptivo; no cambia el orden).
7. **Directores favoritos**: un director con al menos 2 títulos tuyos y promedio por encima de tu nota media (hasta 3). Sus títulos se marcan
   con "De tus directores favoritos" y **suben 0,4 puntos** en el orden *Recomendado* (`DIRECTOR_BOOST` en `docs/js/profile.js`). Es un impulso
   chico y fijo, no una predicción: con 2 títulos por director hay poca evidencia, así que solo desempata entre notas parecidas.

El análisis de gusto (`docs/js/taste.js`) es solo estadística descriptiva de tus notas: promedios por género y
director, y cuánto te separás de la nota de IMDb.

El modelo entrenado del proyecto personal (RandomForest sobre el desvío vs. IMDb, `03_modeling/build_model.py`) sigue en este
mismo directorio y se documenta en [`modeling.md`](modeling.md).
