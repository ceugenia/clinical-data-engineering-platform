.PHONY: install generate run run-no-dbt simulate test lint format dashboard docker

install:
	python -m pip install -e ".[dev]"

generate:
	python -m clinical_pipeline generate

run:
	python -m clinical_pipeline run

run-no-dbt:
	python -m clinical_pipeline run --no-dbt

simulate:
	python -m clinical_pipeline simulate

test:
	pytest --cov=clinical_pipeline --cov-report=term-missing

lint:
	ruff check .

format:
	ruff format .

dashboard:
	streamlit run app/streamlit_app.py

docker:
	docker compose up --build
