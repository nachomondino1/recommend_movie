# 4. Modeling

## Formulaciones probadas
1. **Regresión directa** — predecir `Your Rating` (1–10).
2. **Regresión del desvío** — predecir `Your Rating − IMDb Rating` y reconstruir
   `pred = IMDb Rating + desvío_predicho`. **Resultó la mejor.**
3. **Clasificación binaria** — `Your Rating ≥ 7` ("me gustó de verdad").

## Validación
Validación cruzada 5-fold (`KFold` para regresión, `StratifiedKFold` para
binario). Con 126 filas un solo split train/test es demasiado ruidoso.

## Iteraciones de features
| Iteración | Qué agregó | Mejor binario (ROC AUC) | Mejor MAE |
|---|---|---|---|
| v1 (`modeling/model.py`) | géneros + numéricas IMDb | — | 1.42 (no gana) |
| 3A (`modeling/classify.py`) | reformulación binaria | 0.61 | — |
| 3B (`modeling/model_v2.py`) | director (TE), franquicia, antigüedad | 0.62 | 1.36 (no gana) |
| C (`modeling/train.py`) | sinopsis (TF-IDF+SVD), keywords, idioma, métricas TMDB | 0.63 | **1.26** (desvío + RF) |

## Resultado actual (`modeling/train.py`)
```
REGRESIÓN
  Baseline: media de tu nota          MAE 1.31
  Regla fija: IMDb + media(desvío)    MAE 1.29
  RandomForest (desvío)               MAE 1.26   <- mejor
BINARIO (>=7)   baseline 55%
  Gradient Boosting                   acc 60% / balanced 0.59 / AUC 0.63
```

## Lectura
- El texto de la sinopsis, solo, **no tiene señal** (KNN sobre TF-IDF: AUC ~0.50).
- La mejora total sobre el baseline es real pero chica (~5% MAE, +0.13 AUC).
- **El cuello de botella es la cantidad de datos, no las features.** Tres
  expansiones de features no movieron el techo por encima de AUC ~0.63.

## Próximos pasos candidatos
- **Más ratings** (opción D): de 126 a 300+ habilitaría que las features de texto
  entrenen de verdad.
- Ensemble regresión-desvío + clasificador para un score único y coherente.
- Probar embeddings de sinopsis (sentence-transformers) en lugar de TF-IDF.
