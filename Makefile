# Interfaz del proyecto. Correr `make` para ver los comandos.
PY := ./venv/bin/python
PORT ?= 8765

.PHONY: help serve sync setup update eval robust results drivers explore predict watched skip

help:
	@echo "make serve                        - correr el sitio en local: http://localhost:$(PORT)  (PORT=9000 para otro puerto)"
	@echo "make sync                         - actualizar el catálogo de TMDB y commitear en staging (./sync_data.sh)"
	@echo "make setup                        - crear venv e instalar dependencias (una vez)"
	@echo "make update                       - re-enriquecer TMDB, re-entrenar, re-puntuar y regenerar el dashboard"
	@echo "make predict TITLE=\"X\"            - nota predicha para un título por nombre"
	@echo "make watched TITLE=\"X\" RATING=N   - marcar como vista y puntuada (agrega a data/01_data_understanding/imdb/ratings.csv)"
	@echo "make skip TITLE=\"X\"               - marcar 'no me interesa' (se saca del dashboard sin puntuar)"
	@echo "make eval                         - diagnósticos: modelos (CV) + curva de aprendizaje + trayectoria + reseñas"
	@echo "make robust                       - prueba de robustez: ¿algún modelo le gana a la nota de IMDb? (~80 s)"
	@echo "make results                      - dejar los resultados de make robust listos para la portada de la web (docs/v3/data/model_results.json)"
	@echo "make drivers                      - versión alternativa: qué variables explican la nota pública de TMDB (sin tus notas)"
	@echo "make explore                      - análisis exploratorio (gráficos en data/01_data_understanding/exploration/)"
	@echo
	@echo "Flujo habitual: actualizás los CSV de data/01_data_understanding/imdb/ -> make update (el dashboard queda en data/05_deployment/)"

serve:
	@echo "Sitio en http://localhost:$(PORT)  (Ctrl+C para frenarlo)"
	python3 -m http.server $(PORT) --directory docs

sync:
	./sync_data.sh

setup:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	test -f .env || cp .env.example .env
	@echo "Listo. Completá TMDB_TOKEN en .env"

update:
	$(PY) 01_data_understanding/tmdb_data.py
	$(PY) 02_data_preparation/prepare_tmdb.py
	$(PY) 03_modeling/build_model.py
	$(PY) 03_modeling/build_model.py catalog
	$(PY) 05_deployment/dashboard.py

predict:
	@$(PY) 03_modeling/build_model.py predict "$(TITLE)"

watched:
	@$(PY) 02_data_preparation/curate.py watched "$(TITLE)" "$(RATING)"

skip:
	@$(PY) 02_data_preparation/curate.py skip "$(TITLE)"

eval:
	$(PY) 03_modeling/build_model.py
	$(PY) 03_modeling/assess_model.py

robust:
	$(PY) 03_modeling/assess_model.py --only-robust

results:
	$(PY) 05_deployment/build_results.py

drivers:
	$(PY) 02_data_preparation/prepare_titles.py
	$(PY) 03_modeling/drivers_model.py

explore:
	$(PY) 01_data_understanding/exploration.py
