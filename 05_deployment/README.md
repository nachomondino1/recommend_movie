# Fase 5 — Despliegue

## Ramas

| Rama | Rol |
|---|---|
| `staging` | Donde se hacen y prueban **todos** los cambios (código y datos). |
| `prod` | Lo que ve el público. Solo recibe cambios por pull request desde `staging`. |

Promover a producción:

```bash
gh pr create --base prod --head staging --title "..." --body "..."
```

La página publicada es `docs/` (HTML + CSS + JS sin build): `index.html` (la portada: el proyecto, con el flujo CRISP-DM y los resultados del modelado; lee `docs/v3/data/model_results.json`) y `numero.html` (cargar tus datos de IMDb, ver tu desvío contra IMDb y predecir la nota de cualquier título: IMDb + tu número); el JS de cada una está en `docs/js/pages/` y lo compartido en `docs/js/shared.js`. El dashboard del proyecto personal original quedó guardado, sin publicar, en `docs/old_version/dashboard_personal.html` (git-ignored). Para que sirva `prod`, en GitHub → Settings → Pages el origen debe ser la rama `prod`, carpeta `/docs`. Hoy Pages apunta a otra rama: cambiarlo es una decisión tuya, no se hace desde el código.

## Actualizar los datos

```bash
./sync_data.sh                 # recolecta de TMDB, arma el catálogo, commitea y pushea a staging
./sync_data.sh --top 800       # cualquier argumento va tal cual a refresh_tmdb_data.py
```

Cada corrida suma una fila a `01_data_understanding/refresh_log.md`. Después, pull request a `prod`.

## Correr el sitio en local

```bash
make serve                                # abrir http://localhost:8765/  (PORT=9000 para otro puerto)
# sin make: cd docs && python3 -m http.server 8765
```

## Qué guarda el navegador del visitante

Solo en su `localStorage`: los dos archivos de IMDb que subió (ya parseados) y las plataformas que eligió. Nada se envía a ningún servidor. Botón "Borrar mis datos" en la página.
