# 1. Business Understanding

## Objetivo de negocio
Decidir, **antes de ver** una película o serie, si al usuario le va a gustar —
para priorizar la watchlist y evitar perder tiempo en títulos que no va a disfrutar.

## Objetivo de data mining
Dado el historial de notas del usuario en IMDb (1–10), predecir la nota que le
pondría a un título nuevo, o al menos si la disfrutaría o no.

## Criterios de éxito
| Nivel | Métrica | Umbral |
|---|---|---|
| Mínimo (útil) | ROC AUC en clasificación "nota ≥ 7" | > 0.65, superando el baseline (~0.50) |
| Bueno | ROC AUC | > 0.75 |
| Regresión (aspiracional) | MAE de la nota | < 1.20 (baseline media ≈ 1.33) |

## Supuestos y restricciones
- Dataset chico: 126 títulos puntuados. Techo de complejidad de modelo acotado.
- El usuario puntúa distinto que la media de IMDb (más duro, correlación ~0.29),
  así que la nota pública no alcanza como predictor.
- Sin costo de infraestructura: todo corre local. TMDB tiene API gratuita.

## Plan
Seguir CRISP-DM. Iterar: features → modelo → evaluación, sumando fuentes de
señal (metadatos IMDb → contenido TMDB → texto de sinopsis).
