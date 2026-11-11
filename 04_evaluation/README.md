# Fase 4 — Evaluación

**Proyecto personal:** `evaluate.py` compara modelos (CV), calcula la curva de aprendizaje, la trayectoria real de scores y los insights de reseñas (`make eval`).

**MVP público:** pendiente. Todavía no hay una forma de medir si la lista le sirve a alguien.

Qué medir cuando haya datos:
- **Con tus datos:** esconder una parte de tus notas, puntuarlas con la regla usando el resto y comparar (correlación y error medio contra tu nota real, y contra la nota de IMDb sola como línea base).
- **Cobertura del catálogo:** qué porcentaje de las watchlists de prueba aparece en el catálogo (`verify_data_quality.py` mide la cobertura del lado del catálogo, no del usuario).
- **Uso real:** si alguien usa el sitio y qué hace (hoy no hay analítica).
