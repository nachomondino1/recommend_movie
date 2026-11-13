# 1. Business Understanding

## Versión 2 (la actual): ¿qué hace que una película tenga buena nota?

### Objetivo de negocio
Entender qué características de una película o serie se asocian con una nota pública alta o baja, para poder contárselo a
cualquier persona interesada: ¿importan más el género, la duración, el elenco o el director?

### Objetivo de data mining
Dado el catálogo de TMDB (8.493 títulos, 6.774 con al menos 100 votos), predecir la nota pública (1 a 10) a partir de las
características del título, y medir qué grupos de variables pesan más. Aprendizaje supervisado, regresión. Una sola fuente:
la API de TMDB.

### Criterios de éxito
- Predecir mejor que el promedio, en datos que el modelo no vio (error medio menor que el de predecir siempre el promedio).
- Poder decir qué variables pesan, con intervalos de confianza y pruebas de robustez.

### Supuestos y restricciones
- Las variables no incluyen ninguna opinión (ni votos ni popularidad del título): dependen de la nota, no la explican.
- El catálogo son los títulos disponibles en plataformas (los más populares de cada una): hay sesgo de selección.
- Las asociaciones no son causas.

---

## Versión 1 (archivada): la nota personal

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
