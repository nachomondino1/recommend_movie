# Playbook: flujo de datos para proyectos personales chicos (datos → modelo → dashboard)

Este documento describe un **patrón de arquitectura**, no este proyecto puntual.
Sirve para arrancar un proyecto nuevo (de cualquier tema: películas, finanzas
personales, hábitos, lo que sea) que tenga esta forma:

- Hay una fuente de datos propia, chica, que el usuario alimenta a mano o
  re-exporta cada tanto.
- Esos datos se enriquecen con una API externa (gratis o con rate limit).
- Se entrena un modelo simple sobre esos datos.
- El resultado se muestra en un dashboard que el usuario mira seguido.
- Todo lo corre **una persona**, no un equipo — por eso la prioridad es
  simplicidad y pocos comandos, no robustez de producción.

Pegá este archivo en el repo nuevo (o resumíselo a Claude al arrancar) y
decime qué es la fuente de datos, qué API enriquece, y qué predice el modelo
— el resto del armado sale de calcar esta estructura.

## El flujo, en una línea

```
datos crudos editables (CSV versionado)
    → enriquecimiento externo con caché (gitignored)
    → feature engineering
    → entrenar/cargar modelo (gitignored, se regenera)
    → puntuar datos nuevos → CSV de salida (gitignored)
    → dashboard estático (HTML con los datos embebidos)
    → publicar (GitHub Pages u otro estático)
```

Un `Makefile` con comandos de una palabra (`make update`, `make publish`) es
la única interfaz. El usuario nunca corre `python -m src.algo` a mano ni
piensa en el orden de los módulos.

## Las 3 categorías de archivos (la regla que más importa)

Todo archivo del proyecto cae en una de tres categorías. Confundirlas es el
error más común al arrancar:

1. **Fuente de verdad, versionada.** Los CSV que el usuario edita a mano o
   re-exporta (`data/ratings.csv`, `data/watchlist.csv` en este proyecto).
   Chicos, legibles, versionados en git porque son el único dato que no se
   puede regenerar.
2. **Derivado, regenerable, gitignored.** Todo lo que sale de correr el
   pipeline sobre (1): caché de la API externa (`data/cache/`), modelos
   entrenados (`models/`), CSVs/gráficos de salida (`outputs/`). Si se borra
   la carpeta entera, `make update` la reconstruye. Por eso nunca va a git.
3. **Código + docs.** `src/`, `Makefile`, `docs/` (si hay narrativa del
   proyecto). Versionado, obviamente.

Regla rápida para decidir dónde va algo nuevo: **¿se puede recalcular
corriendo el pipeline sobre los CSV de (1)?** Si sí, va gitignored en (2).
Si no — es un dato que el usuario aportó y no existe en ningún otro lado —
va versionado en (1), aunque sea un CSV chiquito nuevo (ejemplo real: cuando
se agregó "marcar como no me interesa", se creó `data/excluded.csv`
versionado, no una columna derivada).

## Los módulos de `src/` (uno por responsabilidad)

> En este repo los módulos viven repartidos en las carpetas por fase CRISP-DM (`01_data_understanding/` … `05_deployment/`) en vez de un `src/` único; cada script arma su propio `sys.path`, así que se corren directo (`python 03_modeling/model.py`) o con `make`.

Cada uno hace una sola cosa y se puede correr solo con `python -m src.X`
para debuggear. El `Makefile` los encadena en el orden correcto.

- **`config.py`** — paths del proyecto (todas las constantes `*_CSV`,
  `*_DIR` en un solo lugar) + carga de `.env` sin dependencias (parsing
  manual de `CLAVE=valor`, `.setdefault` para no pisar env vars ya puestas).
  Todo lo demás importa de aquí, nunca hardcodea un path.
- **`data.py`** — carga de los CSV fuente + **cliente de la API externa**.
  El cliente:
  - cachea cada respuesta en disco, un archivo por entidad (`data/cache/tmdb/{id}.json`
    en este proyecto), clave estable (el id externo, no el nombre).
  - antes de pedir, mira si ya está cacheado — si sí, no vuelve a pegarle a
    la API.
  - soporta **backfill**: si el cache existe pero le falta un campo nuevo
    (porque se agregó esa feature después), pide *solo* ese campo extra, no
    vuelve a pedir el detalle completo. Esto importa en cuanto el proyecto
    tiene más de ~50 entidades cacheadas — sin esto, cada feature nueva
    significa re-pagar todas las requests.
  - maneja rate limit (429 → `Retry-After` + reintento) y 404 (entidad no
    encontrada → dict vacío, no excepción).
- **`features.py`** — construye `X`/`y` para el modelo. Clave: tiene **dos
  entradas a la misma lógica**: `build()` desde el CSV completo (para
  entrenar) y `build_row()`/`build_rows()` para una o N entidades sueltas
  (para predecir algo que no está en ningún CSV todavía). Ambas delegan a un
  `_engineer()` privado compartido — si la lógica de features vive en dos
  lugares separados, en algún momento se desincroniza.
- **`pipeline.py`** — el pipeline de sklearn (o la librería que sea) **en su
  propio módulo**, separado de `model.py`. Motivo concreto: si el pipeline
  tiene una clase custom (un transformer, un encoder) y vive en el mismo
  módulo que se ejecuta como `__main__`, el pickle del modelo guardado no se
  puede cargar después (`pickle` necesita poder importar la clase por su
  módulo real). Separarlo evita este bug, que es silencioso hasta que
  alguien intenta cargar el modelo desde otro script.
- **`model.py`** — `fit_and_save()` (entrena, guarda modelo(s) +
  metadata + una fila en un historial de métricas versionado) y
  `load_models()` con **re-train perezoso**: compara el `mtime` del CSV
  fuente contra el `mtime` del modelo guardado, y si el CSV es más nuevo,
  reentrena solo antes de cargar. Así el usuario nunca corre "entrenar" como
  paso separado — pasa automáticamente la primera vez que algo pide el
  modelo después de haber editado los datos. También vive aquí el scoring:
  aplicar el modelo ya entrenado a datos nuevos y guardar el CSV de salida.
- **`dashboard.py`** — genera **un solo HTML autocontenido**: los datos de
  salida se vuelcan como JSON embebido dentro del `<script>` del HTML, JS
  vanilla sin build step ni librerías pesadas. No hay servidor ni API en
  runtime — el HTML ya tiene todo adentro. Esto es lo que hace que
  "publicar" sea trivial (copiar un archivo a `docs/`) y que GitHub Pages
  alcance sin backend.
- **Módulos de "curación" chicos** (`curate.py`, `review.py` en este
  proyecto) — comandos de una línea para que el usuario anote su propio
  dataset sin editar CSVs a mano: resuelven el nombre/id contra la misma API
  externa que ya usa `data.py` (reusar el cliente, no duplicar lógica de
  búsqueda) y hacen upsert en el CSV fuente correspondiente.

## El `Makefile`

Encadena los módulos, nunca al revés (`src/` no sabe que existe el
Makefile). Convención de targets que funcionó bien:

```makefile
setup:    # venv + pip install + copiar .env.example -> .env (una vez)
update:   # data -> model -> (catálogo/scoring extra) -> dashboard, en ese orden
eval:     # diagnósticos (métricas, curva de aprendizaje) sin tocar outputs de producción
predict:  # ad-hoc, una entidad suelta por nombre, sin pasar por CSV
publish:  # git add docs/ + commit + push (deploy = commit a main con Pages apuntando a /docs)
```

`make` sin argumentos (target `help`) imprime qué hace cada comando y cuál
es el flujo habitual en una línea — así un chat nuevo de Claude (o el
usuario seis meses después) no tiene que leer el Makefile entero para saber
qué correr.

## Credenciales

`.env` (gitignored) + `.env.example` (versionado, con las claves sin
valores) en la raíz. `config.py` lo parsea a mano — no hace falta
`python-dotenv` para 3 líneas. Si el usuario pega un token real en el chat,
asumir que está comprometido y pedirle que lo regenere.

## Checklist para arrancar un proyecto nuevo con este patrón

1. ¿Cuál es el CSV fuente que el usuario va a editar/re-exportar? Definir sus
   columnas primero, todo lo demás depende de esto.
2. ¿Qué API externa enriquece cada fila, y con qué id estable se cachea cada
   entidad?
3. ¿Qué predice el modelo, y con qué variable objetivo del CSV fuente?
4. Armar `config.py` con los paths antes que nada — evita el reflejo de
   hardcodear paths en cada módulo.
5. `data.py` (carga + cliente con caché) → `features.py` (`build()` +
   `build_row()`) → `pipeline.py` → `model.py` (`fit_and_save()` +
   `load_models()` con re-train perezoso) → `dashboard.py`.
6. `Makefile` con `setup`/`update`/`publish` como mínimo.
7. `.gitignore`: todo lo de la categoría 2 (cache, models, outputs, venv,
   .env) desde el primer commit, antes de que algo pesado se cuele al repo.

## Lecciones operativas (no son del dominio, son de cómo trabajar)

- **Sesiones paralelas de Claude Code sobre el mismo repo:** si `make
  update` o un módulo falla con un error que no tiene sentido con los
  cambios propios, correr `ListAgents` antes de asumir un bug — puede haber
  otra sesión editando el mismo archivo en vivo. Coordinar por `SendMessage`
  en vez de pisar a ciegas.
- **Probar el dashboard generado** antes de dar por terminada una fase:
  regenerar solo el HTML (no todo `make update`) si los CSV de `outputs/`
  ya existen, abrirlo en el browser pane, probar explícitamente en mobile
  (375px) y no solo desktop — la mayoría de los bugs de layout en este tipo
  de dashboard aparecen solo en mobile.
- **No sobre-diseñar desde el día uno.** Arrancar con los módulos mínimos
  (`data`, `features`, `model`, `dashboard`) y agregar módulos de curación o
  catálogos ampliados solo cuando haya un pedido concreto — la estructura
  por fases (CRISP-DM u otra) ayuda a no mezclar "lo que ya funciona" con
  "lo que se está probando".

## Variante multiusuario: catálogo precomputado, sitio sin API (2026-11-11)

Cuando el proyecto pasa de "una persona" a "cualquiera que abra la página" (caso: el sitio de `docs/`):

- **El pipeline Python deja de correr por usuario.** Corre una vez en la máquina del autor y publica un **catálogo estático** (`docs/data/catalog.json`); el navegador del visitante solo lo lee y lo cruza con sus propios datos (ej. su export de IMDb, parseado localmente y guardado en `localStorage`).
- **Nada de tokens en el cliente ni llamadas a la API desde el sitio:** sin token público, sin rate limits, carga instantánea, y **todas** las llamadas salen de los scripts de recolección, así que se pueden registrar.
- **Log de uso de la API:** cada corrida real del script de recolección agrega una fila a `01_data_understanding/refresh_log.md` (fecha, opciones, requests totales y por endpoint, nuevos, cambiados, errores, duración). Mismo patrón que `boardgame`.
- **Estructura por fases CRISP-DM** (`01_data_understanding/` … `05_deployment/`), crudos en `data/01_data_understanding/` (gitignoreados), catálogo del sitio versionado, `sync_data.sh` que lo regenera y commitea en `staging`; `prod` solo recibe pull requests desde `staging`.
- **Sin modelo ni score personalizado:** con ~100 notas por usuario no hay señal suficiente (el proyecto personal lo confirmó: el modelo apenas supera "IMDb − 1.3"). La lista se ordena por la nota ponderada por votos (como el Top 250 de IMDb), filtrada por plataformas y sin lo ya visto; lo único personal es marcar los géneros favoritos (ver `03_modeling/README.md`).
- **Trade-off aceptado:** un título del historial que no esté en el catálogo se trata como "no disponible en tus plataformas".

## Diseño del sitio público (2026-11-11)

- **Landing según `DESIGN_PLAYBOOK_unificado.md` §12:** header sticky angosto separado del hero; hero `min-height: calc(100vh - header)` con foto (`docs/media/hero.jpg`, créditos en `05_deployment/image_credits.md`) bajo un degradé oscuro que se funde con `--bg`; título `clamp(2rem, 5vw, 3.2rem)` peso 800 con dos palabras clave en colores fijos (ámbar y violeta suave, no tokens de tema); un solo CTA que scrollea a la segunda sección (los 3 pasos). Al guardar los datos se pasa a la página "Qué ver"; para quien vuelve, el CTA pasa a "Ver mis recomendaciones".
- **Tres páginas HTML, sin router:** `index.html` (hero + 2 pasos), `que-ver.html` y `mi-gusto.html`. El estado viaja en `localStorage` (archivos del usuario y plataformas). Encabezado y pie se escriben una sola vez en `docs/js/shared.js` (`renderSite`), y el menú muestra "Qué ver" y "Mi gusto" solo cuando ya hay datos. Un JS por página en `docs/js/pages/`; la lógica común en `profile.js`, `taste.js` y `catalog.js`.
- **Divergencias deliberadas del playbook de diseño, por legibilidad (el autor es disléxico):** base 18px y `line-height` 1.7, una sola columna de 760px, sin etiquetas en mayúscula sostenida, sin cursivas, botones de al menos 44-48px de alto, `letter-spacing` levemente positivo en el cuerpo y mucho aire entre bloques. El playbook unificado pide base 14px y eyebrows en mayúsculas; acá se invierte a propósito. Si se quiere unificar, esta es la divergencia a registrar en el apéndice "decisiones al unificar".
- **`docs/` es solo el sitio publicado:** HTML, `css/`, `js/`, `data/` y `media/`; **ningún `.md`** (Pages los serviría como archivos públicos). La narrativa y los créditos viven en la carpeta de la fase que corresponde (`00_business_understanding/` … `05_deployment/`).
- **Desktop sin resignar mobile:** el diseño parte de mobile (una columna, letra grande) y desde 900px agrega grillas: contenedor `--max-w: 1160px` (antes 760px), lista en 2 columnas, pasos 2 y 3 en paralelo (en "Qué ver", "Elegí por mí" y el buscador siguen en una fila cada uno: probados lado a lado y descartados), "Mi gusto" en 2×2. El texto corrido sigue limitado en `ch` para leerse bien aunque el contenedor sea ancho. Los grids se declaran en bloques `@media (min-width: 900px)` al final de `style.css`, así mobile no cambia.
- **Plataformas como filtro, no como paso (2026-11-11):** el inicio solo pide los archivos de IMDb (2 pasos, datos que se cargan una vez). Las plataformas se eligen en "Qué ver" con una lista desplegable con casillas, de selección múltiple (`mvp_platforms_v2` en `localStorage`): sirven igual para "las que pago" y para "hoy solo Netflix". Sin ninguna elegida no se filtra por plataforma. Se descartó guardar "mis plataformas" aparte de un filtro de "hoy": más complejo para poco beneficio.
