install:
	pip install -e ".[dev]"
generate:
	python -m clinical_pipeline generate
run:
	python -m clinical_pipeline run
test:
	pytest
lint:
	ruff check .
dashboard:
	streamlit run app/streamlit_app.py
