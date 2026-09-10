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

## Curva de aprendizaje (`modeling/learning_curve.py`)
Entrenando con subconjuntos crecientes de los 126 títulos:

| n entrenamiento | MAE regresión | AUC binario |
|---|---|---|
| 25  | 1.35 | 0.46 |
| 46  | 1.44 | 0.59 |
| 67  | 1.33 | 0.61 |
| 89  | 1.33 | 0.62 |
| 100 | 1.30 | 0.65 |

- **El binario NO saturó**: la AUC sube de forma sostenida y sin amesetarse de
  n≈45 a n≈100 (0.59 → 0.65). Extrapolando (con cautela), n≈200–300 podría
  acercarse a AUC 0.72–0.78.
- La regresión mejora más despacio y con más ruido, pero también tiende a la baja.
- **Conclusión: el modelo está limitado por datos, no por sesgo.** Más ratings es
  la inversión con mejor retorno esperado.

## Próximos pasos candidatos
- **Más ratings** (opción D, prioritario): re-exportar `ratings.csv` de IMDb cada
  vez que se puntúen títulos nuevos y re-correr el pipeline + la curva.
- Ensemble regresión-desvío + clasificador para un score único y coherente.
- Probar embeddings de sinopsis (sentence-transformers) en lugar de TF-IDF, recién
  cuando haya más datos.
