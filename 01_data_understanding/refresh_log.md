# Registro de actualizaciones de TMDB

Una fila por cada corrida real de `refresh_tmdb_data.py` (la escribe el script solo, no a mano). "Requests" es el total de llamadas a la API de TMDB de esa corrida.

| Fecha | Opciones | Requests | Por endpoint | Títulos en catálogo | Detalles pedidos | Nuevos | Con plataformas distintas | Errores | Duración |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-11 | `--region AR --top 400 --providers 20 --max-age-days 30` | 4316 | discover/movie: 188, discover/tv: 128, genre/movie: 1, genre/tv: 1, movie: 2254, tv: 1742, watch/providers: 2 | 3996 | 3996 | 3996 | 3996 | 0 | 3 min 4 s |
| 2026-11-11 | `--region AR --top 400 --providers 30 --max-age-days 30` | 1337 | discover/movie: 253, discover/tv: 150, genre/movie: 1, genre/tv: 1, movie: 839, tv: 91, watch/providers: 2 | 4918 | 930 | 922 | 1080 | 0 | 0 min 53 s |
| 2026-11-11 | `--region AR --top 400 --providers 100 --max-age-days 30` | 4507 | discover/movie: 612, discover/tv: 306, genre/movie: 1, genre/tv: 1, movie: 2713, tv: 872, watch/providers: 2 | 8493 | 3585 | 3575 | 6071 | 0 | 3 min 2 s |
| 2026-11-11 | `--region AR --top 400 --providers 100 --max-age-days 30` | 9415 | discover/movie: 612, discover/tv: 306, genre/movie: 1, genre/tv: 1, movie: 5805, tv: 2688, watch/providers: 2 | 8493 | 8493 | 0 | 8493 | 0 | 3 min 57 s |
