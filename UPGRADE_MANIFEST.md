# Clinical Data Engineering Platform v2 Upgrade Bundle

This is an **overlay**, not a full repository export. Extract its contents into the existing project root. It does not contain `.git`, `.venv`, generated `data/`, the DuckDB warehouse, or dbt target/log artifacts.

## Replaced files

- `.gitignore`
- `.github/workflows/ci.yml`
- `Dockerfile`
- `Makefile`
- `README.md`
- `app/streamlit_app.py`
- `dbt/models/marts/schema.yml`
- `docs/architecture.md`
- `docs/data_dictionary.md`
- `pyproject.toml`
- `requirements.txt`
- `src/clinical_pipeline/__main__.py`
- `src/clinical_pipeline/config.py`
- `src/clinical_pipeline/ingest.py`
- `src/clinical_pipeline/transform.py`
- `tests/test_ingest.py`
- `tests/test_transform.py`

## New files

- `.dockerignore`
- `UPGRADE_MANIFEST.md`
- `app/dashboard_queries.py`
- `dbt/models/marts/fct_lab_result.sql`
- `dbt/models/marts/mart_lab_analyte.sql`
- `dbt/models/marts/mart_site_performance.sql`
- `dbt/tests/assert_reference_ranges_valid.sql`
- `docker-compose.yml`
- `docs/decisions.md`
- `docs/runbook.md`
- `src/clinical_pipeline/quality.py`
- `tests/test_quality.py`

## Preserved existing implementation

The existing `incremental.py`, `runner.py`, `simulate_changes.py`, `generate.py`, dbt profile, and other working files are not replaced by this bundle. The current timestamp-aware per-record DuckDB upsert behavior is preserved.

## Important scope notes

1. Bronze ingestion now stages each batch and publishes it only after all Parquet files, `manifest.json`, and `_SUCCESS` are present.
2. Silver transformation ignores incomplete Bronze directories.
3. The quality report records validation success, row counts, and deduplicated rows. Structural and referential-integrity failures still fail the batch. This bundle does **not** silently discard invalid rows or implement a rejected-record quarantine.
4. The current incremental path still reads complete CSV/Bronze/Silver snapshots and then performs timestamp-aware upserts. It is not source-side CDC. A true CDC implementation needs a monotonic source event sequence/offset and an append-only source change log.
5. dbt adds lab-result and site-performance models. The Streamlit dashboard adds filters and pipeline/quality monitoring.
6. CI runs Python tests, Ruff, the full pipeline/dbt build, and a Docker image build.

## Validation status

Python files in this bundle were syntax-compiled. The complete integration suite and dbt build must be run in the user's project environment after installing dependencies.
