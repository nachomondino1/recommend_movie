# Interfaz del proyecto. Correr `make` para ver los comandos.
PY := ./venv/bin/python

.PHONY: help setup update eval explore publish

help:
	@echo "make setup    - crear venv e instalar dependencias (una vez)"
	@echo "make update   - re-enriquecer TMDB, re-entrenar, re-puntuar y regenerar el dashboard"
	@echo "make eval     - diagnósticos: comparación de modelos (CV) + curva de aprendizaje"
	@echo "make explore  - análisis exploratorio (gráficos en outputs/)"
	@echo "make publish  - subir el dashboard a GitHub Pages (git add docs + commit + push)"
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

eval:
	$(PY) -m src.model --eval

explore:
	$(PY) -m notebooks.exploration

publish:
	git add docs/index.html docs/.nojekyll
	git commit -m "Actualizar dashboard" && git push
