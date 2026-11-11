# Interfaz del proyecto. Correr `make` para ver los comandos.
PY := ./venv/bin/python
PORT ?= 8765

.PHONY: help serve sync setup update eval explore predict watched skip review

help:
	@echo "make serve                        - correr el sitio en local: http://localhost:$(PORT)  (PORT=9000 para otro puerto)"
	@echo "make sync                         - actualizar el catálogo de TMDB y commitear en staging (./sync_data.sh)"
	@echo "make setup                        - crear venv e instalar dependencias (una vez)"
	@echo "make update                       - re-enriquecer TMDB, re-entrenar, re-puntuar y regenerar el dashboard"
	@echo "make predict TITLE=\"X\"            - nota predicha para un título por nombre"
	@echo "make watched TITLE=\"X\" RATING=N   - marcar como vista y puntuada (agrega a data/ratings.csv)"
	@echo "make skip TITLE=\"X\"               - marcar 'no me interesa' (se saca del dashboard sin puntuar)"
	@echo "make review TITLE=\"X\" LIKED=\"...\" DISLIKED=\"...\" - guardar tu reseña (qué te gustó / qué no)"
	@echo "make eval                         - diagnósticos: modelos (CV) + curva de aprendizaje + trayectoria + reseñas"
	@echo "make explore                      - análisis exploratorio (gráficos en outputs/)"
	@echo
	@echo "Flujo habitual: actualizás data/ratings.csv o data/watchlist.csv -> make update (el dashboard queda en archive/dashboard_personal.html)"

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
	$(PY) 03_modeling/model.py
	$(PY) 03_modeling/catalog.py
	$(PY) 05_deployment/dashboard.py

predict:
	@$(PY) 03_modeling/predict.py "$(TITLE)"

watched:
	@$(PY) 01_data_understanding/curate.py watched "$(TITLE)" "$(RATING)"

skip:
	@$(PY) 01_data_understanding/curate.py skip "$(TITLE)"

review:
	@$(PY) 01_data_understanding/review.py "$(TITLE)" --liked "$(LIKED)" --disliked "$(DISLIKED)"

eval:
	$(PY) 03_modeling/model.py
	$(PY) 04_evaluation/evaluate.py

explore:
	$(PY) 01_data_understanding/exploration.py
