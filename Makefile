# Interfaz del proyecto. Correr `make` para ver los comandos.
PY := ./venv/bin/python

.PHONY: help setup update eval explore predict watched skip publish

help:
	@echo "make setup                        - crear venv e instalar dependencias (una vez)"
	@echo "make update                       - re-enriquecer TMDB, re-entrenar, re-puntuar y regenerar el dashboard"
	@echo "make predict TITLE=\"X\"            - nota predicha para un título por nombre"
	@echo "make watched TITLE=\"X\" RATING=N   - marcar como vista y puntuada (agrega a data/ratings.csv)"
	@echo "make skip TITLE=\"X\"               - marcar 'no me interesa' (se saca del dashboard sin puntuar)"
	@echo "make eval                         - diagnósticos: modelos (CV) + curva de aprendizaje + trayectoria"
	@echo "make explore                      - análisis exploratorio (gráficos en outputs/)"
	@echo "make publish                      - subir el dashboard a GitHub Pages (git add docs + commit + push)"
	@echo
	@echo "Flujo habitual: actualizás data/ratings.csv o data/watchlist.csv -> make update -> make publish"

setup:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	test -f .env || cp .env.example .env
	@echo "Listo. Completá TMDB_TOKEN en .env"

update:
	$(PY) -m src.data
	$(PY) -m src.model
	$(PY) -m src.dashboard

predict:
	@$(PY) -m src.predict "$(TITLE)"

watched:
	@$(PY) -m src.curate watched "$(TITLE)" "$(RATING)"

skip:
	@$(PY) -m src.curate skip "$(TITLE)"

eval:
	$(PY) -m src.model --eval

explore:
	$(PY) -m notebooks.exploration

publish:
	git add docs/index.html docs/.nojekyll
	git commit -m "Actualizar dashboard" && git push
