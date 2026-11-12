# Versión 2: ¿qué hace que una película tenga buena nota?

Una sola fuente (la API de TMDB), sin notas personales. Catálogo de **6.774** títulos con al menos
100 votos (4.768 películas y 2.006 series), de 8.493 en total.
La respuesta es la nota pública de TMDB. Aprendizaje supervisado, regresión. La pregunta es qué variables se asocian con una
nota más alta o más baja, no qué nota le pondría una persona.

```
make drivers      # prepare_titles.py (02) + drivers_model.py (03): data/03_modeling/drivers_results.json
make results      # docs/data/model_results.json para la web
```

Para el elenco y el equipo hace falta antes `fetch_credits.py` (01), que baja los créditos de TMDB.

## Qué tan bien se puede predecir
Validación cruzada de 5 folds repetida 2 veces; todo fuera de muestra.

| Variables | R² | Error medio | Predecir siempre el promedio |
|---|---|---|---|
| Contenido sin elenco ni equipo | 0,59 | 0,48 | 0,77 |
| **Contenido con elenco y equipo** | **0,61** | **0,46** | 0,77 |
| + popularidad y votos (circular) | 0,70 | 0,40 | 0,77 |

Popularidad y votos se dejan afuera del análisis principal: dependen de la nota, no la explican.

## Qué grupos de variables pesan más
Caída del R² al mezclar al azar un grupo en datos no vistos (permutación) y al sacarlo del modelo (ablación). Si difieren
mucho, el grupo comparte información con otros.

| Grupo | Permutación | Sin el grupo |
|---|---|---|
| Formato (serie o película) | 0,33 | 0,003 |
| Géneros | 0,12 | 0,052 |
| Duración | 0,11 | 0,013 |
| Elenco | 0,10 | 0,019 |
| Plataformas | 0,07 | 0,022 |
| Año de estreno | 0,05 | 0,017 |
| Director | 0,04 | 0,005 |
| Guion, música y fotografía | 0,03 | -0,002 |
| Sinopsis (largo) | 0,00 | -0,003 |

Lectura: el formato "pesa" al mezclarlo pero casi nada al sacarlo, porque la duración y los géneros ya lo delatan. Lo que
aporta información propia son los **géneros**, el **elenco**, las **plataformas** y el **año**. El guion, la música y la
fotografía no aportan nada que se distinga del ruido, ni el largo de la sinopsis.

## Efectos ajustados (puntos de nota, IC 95 %, bootstrap de 300 remuestreos)
| Variable | Efecto |
|---|---|
| Es serie (contra película) | +1,26 [+1,19; +1,32] |
| Documental | +0,78 [+0,63; +0,95] |
| Animación | +0,78 [+0,72; +0,84] |
| Elenco más conocido (+10 de popularidad) | +0,44 [+0,30; +0,56] |
| Cada hora más de duración | +0,42 [+0,37; +0,47] |
| Terror | −0,32 [−0,38; −0,25] |
| Música | +0,23 [+0,09; +0,38] |
| Director con 3+ títulos en el catálogo | +0,20 [+0,16; +0,24] |
| Drama | +0,20 [+0,15; +0,24] |
| Historia | +0,15 [+0,05; +0,25] |
| Suspense | −0,13 [−0,19; −0,07] |
| Bélica | +0,12 [+0,01; +0,21] |

## Actores (descriptivo)
Entre 445 actores con al menos 10 títulos, mejor y peor de lo esperable por formato, género,
duración, año y plataformas (residuo fuera de muestra de un modelo sin elenco). Es una asociación, con márgenes de error amplios.

- Mejor: Benedict Cumberbatch (+0,63), Hailee Steinfeld (+0,55), Scott Adkins (+0,44), Tom Holland (+0,40), Chow Yun-fat (+0,38)
- Peor: Dakota Johnson (−0,64), Alec Baldwin (−0,62), Danny Glover (−0,58), Adam Sandler (−0,54), Giovanni Ribisi (−0,46)

## Robustez
| Prueba | n | R² | Error medio (promedio) |
|---|---|---|---|
| Votos ≥ 50 | 8.493 | 0,60 | 0,49 (0,81) |
| Votos ≥ 300 | 4.533 | 0,61 | 0,43 (0,72) |
| Votos ≥ 1.000 | 2.759 | 0,60 | 0,41 (0,67) |
| Solo películas | 4.768 | 0,50 | 0,49 (0,70) |
| Solo series | 2.006 | 0,14 | 0,43 (0,49) |

En series casi no se puede predecir la nota con estas variables: son más parejas.

## Cuidados al interpretar
- **Sesgo de selección:** títulos disponibles en plataformas; la ventaja de las series refleja en parte cómo vota la gente cada formato.
- **Correlación, no causa.**
- **Faltan variables:** presupuesto, premios, marketing. El elenco sale de los 5 primeros del reparto.
- **Popularidad de los actores:** sube con sus estrenos recientes, así que se parece a la popularidad del título.
- Una sola semilla de validación cruzada: las conclusiones fuertes (géneros, duración, formato, elenco) son estables; los efectos chicos (año, plataformas) no deberían tomarse al pie de la letra.
- Palabras de la sinopsis: "filmaffinity" aparece asociada a notas bajas porque algunas sinopsis traen esa firma de la fuente. Es un artefacto, no un hallazgo.
