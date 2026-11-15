# Local runbook

## 1. Create the environment

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 2. Run the baseline pipeline

```powershell
python -m clinical_pipeline generate
python -m clinical_pipeline run
```

Expected artifacts:

- `data/bronze/run_id=.../` with four Parquet files, `manifest.json`, and `_SUCCESS`.
- `data/silver/*.parquet`.
- `data/quality/quality_report.json`.
- `data/warehouse/clinical.duckdb`.
- `data/warehouse/pipeline_runs.jsonl`.

## 3. Verify tests and style

```powershell
pytest --cov=clinical_pipeline --cov-report=term-missing
ruff check .
ruff format --check .
```

## 4. Demonstrate timestamp-aware updates

```powershell
python -m clinical_pipeline simulate
python -m clinical_pipeline run --no-generate
```

The simulator updates selected synthetic source records and their `source_updated_at` timestamps. Inspect the JSON result printed by the pipeline for inserted, updated, and unchanged row counts.

## 5. Start the dashboard

```powershell
streamlit run app/streamlit_app.py
```

## 6. Run with an external data directory

```powershell
$env:CLINICAL_DATA_DIR = "D:\clinical-platform-data"
python -m clinical_pipeline generate
python -m clinical_pipeline run
streamlit run app/streamlit_app.py
```

## 7. Troubleshooting

- If dbt is not found, activate `.venv` and reinstall with `python -m pip install -e ".[dev]"`.
- If the dashboard reports missing dbt models, run `python -m clinical_pipeline run`.
- If source files are missing, run `python -m clinical_pipeline generate`.
- If a transform fails, inspect the failed stage and error in the latest JSONL audit record. Fix or regenerate the synthetic source files, then rerun.
- Incomplete Bronze staging folders are intentionally ignored. A completed run must contain `_SUCCESS`.
