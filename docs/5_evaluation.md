# 5. Evaluation

## Contra los criterios de éxito (doc 1)
| Criterio | Umbral | Estado actual | ¿Cumple? |
|---|---|---|---|
| Mínimo útil | ROC AUC > 0.65 | 0.63 | Casi, no todavía |
| Bueno | ROC AUC > 0.75 | 0.63 | No |
| Regresión | MAE < 1.20 | 1.26 | No (pero supera al baseline 1.31) |

## Interpretación del modelo binario (Gradient Boosting, ≥7)
- Como filtro "¿la veo?": acierta ~60% vs 55% de tirar siempre "sí".
- ROC AUC 0.63 → ordenando por probabilidad, pone antes la que te gustó que la
  que no el 63% de las veces. Sirve como **desempate de la watchlist**, no como
  veredicto.

## Chequeos de sanidad (watchlist puntuada)
- Top: biografía / historia / guerra / drama (Godfather, Hotel Rwanda, Dead
  Poets Society) — coincide con tus géneros preferidos del EDA.
- Fondo: Spy Kids 3, The Time Traveler's Wife — coherente (a esta última le
  pusiste 1).
- **Inconsistencia conocida:** `pred_rating` y `p_like` vienen de dos modelos con
  targets distintos, a veces no concuerdan (ej. serie con pred 7.6 y p_like 0.31).

## Riesgos / sesgos
- Muestra chica y sesgada a lo que el usuario eligió ver.
- Géneros con pocos casos (Música n=4) → sus medias no son confiables.
- El modelo hereda el optimismo de IMDb Rating al reconstruir desde el desvío.

## Decisión
Modelo apto para **sugerir un orden** de la watchlist, no para decidir por el
usuario. Volver a evaluar cuando haya más ratings.
