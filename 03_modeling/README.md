# Fase 3 — Modelado

El MVP público **no entrena ningún modelo**: no hay datos suficientes de un visitante nuevo para eso y
un modelo por usuario exigiría backend. En su lugar usa una regla simple, calculada en el navegador
(`docs/mvp/js/score.js`):

- **Afinidad por género:** promedio de tus notas en los géneros del título (solo géneros con ≥ 3 títulos tuyos).
- **Afinidad por director:** promedio de tus notas en títulos del mismo director (≥ 1).
- **Con señal:** `score = 0.6 × afinidad + 0.4 × nota del catálogo`.
- **Sin señal:** `score = nota del catálogo + tu desvío promedio vs. IMDb` (ej. si puntuás 1.5 menos, se resta).

Se muestra como "para vos" en la lista: un orden sugerido, no una predicción calibrada.

El modelo entrenado del proyecto personal (RandomForest sobre el desvío vs. IMDb, `src/model.py`) sigue en `src/` y se documenta en `docs/4_modeling.md`.
