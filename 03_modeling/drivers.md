# Versión alternativa: ¿qué hace que una película tenga buena nota?

Rama `version-tmdb-variables-de-la-nota`. **No usa tus notas de IMDb.** Usa todo el catálogo de TMDB (8.493 títulos;
6.774 con al menos 100 votos) y la variable respuesta es la **nota pública de TMDB**. Es aprendizaje supervisado
(regresión), pero la pregunta cambia: ya no es "qué nota le pondré yo" sino "qué variables se asocian con una nota más alta
o más baja".

```
make drivers      # prepare_titles.py (02) + drivers_model.py (03): data/03_modeling/drivers_results.json
```

## Qué tan bien se puede predecir
Validación cruzada de 5 folds repetida 2 veces; todo fuera de muestra.

| Variables | R² | Error medio | Si se predice siempre el promedio |
|---|---|---|---|
| Contenido (formato, duración, año, géneros, director, plataformas, largo de sinopsis) | **0,59** | **0,48** | 0,77 |
| + popularidad y cantidad de votos | 0,66 | 0,42 | 0,77 |

A diferencia de predecir tu nota personal (127 títulos, sin mejora sobre IMDb), **acá sí hay señal**: el error baja casi
40 %. Popularidad y votos se dejan afuera del análisis principal: dependen de la nota, no la explican (círculo vicioso).

## Qué variables pesan más
Caída del R² al mezclar al azar un grupo en datos no vistos (importancia por permutación), y caída si el modelo nunca lo
ve (ablación). Cuando las dos difieren mucho, el grupo comparte información con otros.

| Grupo | Permutación | Sin el grupo |
|---|---|---|
| Formato (serie o película) | 0,40 | 0,01 |
| Géneros | 0,19 | 0,07 |
| Duración | 0,14 | 0,02 |
| Director | 0,09 | 0,02 |
| Plataformas | 0,09 | 0,03 |
| Año de estreno | 0,07 | 0,03 |
| Largo de la sinopsis | 0,01 | 0,00 |

Lectura: el formato "pesa" 0,40 al mezclarlo, pero casi nada al sacarlo, porque la duración y los géneros de series ya
lo delatan. Lo que aporta información propia son los **géneros** (0,07), el **año** y las **plataformas** (0,03).

## Efectos ajustados (en puntos de nota, con intervalo de confianza del 95 %)
Regresión con bootstrap (300 remuestreos). Cada efecto es "manteniendo lo demás igual".

| Variable | Efecto |
|---|---|
| Es serie (contra película) | +1,24 [1,18; 1,31] |
| Animación | +0,80 [0,74; 0,86] |
| Documental | +0,76 [0,61; 0,92] |
| Cada hora más de duración | +0,45 [0,39; 0,50] |
| Terror | −0,34 [−0,41; −0,28] |
| Director con 3 o más títulos en el catálogo | +0,22 [0,19; 0,26] |
| Drama | +0,20 [0,16; 0,24] |
| Suspense | −0,12 · Acción −0,10 |

Solo películas: documental +1,04, animación +0,98, cada hora de duración +0,85, terror −0,31, director con trayectoria +0,22.

## Robustez
| Prueba | n | R² | Error medio (promedio) |
|---|---|---|---|
| Votos ≥ 50 | 8.493 | 0,57 | 0,51 (0,81) |
| Votos ≥ 300 | 4.533 | 0,59 | 0,44 (0,73) |
| Votos ≥ 1.000 | 2.759 | 0,57 | 0,41 (0,67) |
| Solo películas | 4.768 | 0,47 | 0,50 (0,70) |
| Solo series | 2.006 | **0,11** | 0,44 (0,49) |

El resultado se sostiene con distintos umbrales de votos. En **series casi no se puede predecir** la nota con estas
variables (las notas son más parejas, 7,7 ± 0,6, contra 6,6 ± 0,9 de las películas).

## Cuidados al interpretar
- **Sesgo de selección:** el catálogo son los títulos disponibles en plataformas (los más populares de cada una). La
  diferencia serie/película (+1,24) refleja en parte cómo vota la gente cada formato y qué series entran al catálogo,
  no una calidad intrínseca.
- **Correlación, no causa.** "Los documentales tienen mejor nota" no dice que filmar un documental mejore una película.
- **Faltan variables:** el crudo no trae elenco, guionista, presupuesto ni premios. **No se puede hablar de actores**
  sin volver a descargar de TMDB con los créditos.
- **Duración:** la relación positiva con la nota en películas (0,32 de correlación; de 6,2 en las de 80 a 100 minutos a 7,4
  en las de más de 150) es conocida; no implica que alargar una película la mejore.
- **Palabras de la sinopsis:** "filmaffinity" aparece asociada a notas bajas porque algunas sinopsis traen esa firma
  de la fuente. Es un artefacto de los datos, no un hallazgo.
- Es una sola semilla de validación cruzada, con 300 remuestreos para los efectos; las conclusiones fuertes (géneros,
  formato, duración) son estables, los efectos chicos (plataformas, año) no deberían tomarse al pie de la letra.
