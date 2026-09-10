# 6. Deployment

## Qué hace hoy
`deployment/predict_watchlist.py`:
1. Entrena con los 126 títulos puntuados:
   - `RandomForestRegressor` sobre el desvío respecto de IMDb → `pred_rating`
   - `GradientBoostingClassifier` sobre `≥ 7` → `p_like`
2. Aplica ambos a los 159 títulos de la watchlist.
3. Escribe `outputs/watchlist_scored.csv` ordenado por `pred_rating` desc.

## Cómo usarlo
```bash
./venv/bin/python data_preparation/enrich_tmdb.py   # solo si cambió la watchlist
./venv/bin/python deployment/predict_watchlist.py
```
Después abrir `outputs/watchlist_scored.csv` y mirar el top como cola de reproducción.

## Cómo interpretar
- `pred_rating`: nota estimada 1–10. Error típico ±1.3, así que un 7.4 vs 7.0 es ruido.
- `p_like`: probabilidad estimada de que le pongas ≥ 7. Útil para ordenar, no como sí/no.
- Confiar en el **orden general** (tercio de arriba vs tercio de abajo), no en el número exacto.

## Pendiente para una v2
- Re-entrenar automáticamente al actualizar `ratings.csv`.
- Un único score coherente (ensemble de los dos modelos).
- Guardar el modelo entrenado (`joblib`) en vez de re-entrenar en cada corrida.
- Script que tome un título suelto (por URL o nombre) y devuelva la predicción.
