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

## Prueba de robustez: ¿algo le gana a la nota de IMDb? (`python 04_evaluation/robustness.py`)
n = 127 notas. CV de 5 folds repetida 10 veces, bootstrap pareado de 5.000 remuestreos sobre los
títulos. La base justa es la nota de IMDb **calibrada** a tu escala (a + b·IMDb), no la cruda
(que tiene MAE 1,67 solo porque vos puntuás más bajo que IMDb).

| Modelo | MAE | ΔMAE vs base (IC 95 %) | AUC (≥7) |
|---|---|---|---|
| Base: IMDb calibrada | 1,284 | — | 0,651 |
| Géneros con encogimiento | 1,273 | −0,011 [−0,033, +0,010] | 0,645 |
| Ridge simple | 1,285 | +0,001 [−0,051, +0,052] | 0,633 |
| Ridge con todas las variables | 1,304 | +0,020 [−0,054, +0,098] | 0,618 |
| RandomForest | 1,230 | −0,054 [−0,119, +0,012] | 0,668 |
| GradientBoosting | 1,220 | −0,063 [−0,140, +0,011] | 0,666 |
| Promedio Ridge + RandomForest | 1,245 | −0,040 [−0,088, +0,010] | 0,654 |

- **Ningún intervalo excluye el cero**: no hay evidencia de que algún modelo le gane a IMDb.
- Los mejores (RandomForest / GradientBoosting) bajan ~0,05–0,06 de MAE, pero se eligieron entre
  9 candidatos, así que esa mejora aparente está inflada por la selección.
- **Poder estadístico:** con 127 títulos solo se detectarían mejoras de ≥ ~0,11 puntos de MAE.
  Una mejora real chica (≤ 0,1) no se puede descartar ni confirmar.
- **Control de permutación** (Ridge simple): al mezclar las demás variables al azar, el 22 % de las
  mezclas iguala o supera al modelo real, o sea que no se distingue de ruido.
- **Curva de aprendizaje repetida:** los modelos se acercan a la base al sumar datos (Ridge−base
  pasa de +0,029 a +0,008; RandomForest de +0,083 a −0,002), pero no la superan dentro del ruido.
