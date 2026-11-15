# Architecture and design decisions

## Data flow

1. Synthetic source CSV files are generated deterministically.
2. Python ingestion writes each source table to a hidden staging directory as Parquet.
3. A JSON manifest and `_SUCCESS` marker are written only after every table is persisted; the staging directory is then renamed to its published `run_id=...` directory.
4. Silver transformation selects the newest completed Bronze batch, validates schemas and business rules, deduplicates by business key and source timestamp, and writes Parquet outputs.
5. A JSON quality report records row counts and successful validation checks.
6. DuckDB upserts insert new business keys and update existing rows only when the incoming `source_updated_at` is newer.
7. dbt builds staging views, dimensions, facts, and aggregate marts.
8. Streamlit reads the dbt models and local quality/audit metadata.

## Atomic Bronze publication

An ingestion run is first written to `.staging_run_id=...`. A batch is not eligible for transformation until `_SUCCESS` exists. The staging directory is renamed on the same filesystem, preventing the transformer from selecting a partially written batch. Historical directories without `_SUCCESS` are treated as incomplete and ignored.

## Incremental processing semantics

The warehouse upsert compares `source_updated_at` for each business key. This protects newer warehouse records from being overwritten by older source versions and makes repeated loads idempotent.

The current source path still reads complete CSV and Parquet snapshots. It is therefore **snapshot-based timestamp-aware upsert**, not source-side CDC. The recorded maximum timestamp is operational metadata only; it is not a global extraction cursor. A global timestamp filter could miss a late-arriving update to an entity whose timestamp is older than another entity's maximum.

A future CDC extension should use a monotonic source event sequence or change-log offset as its extraction cursor, while retaining `source_updated_at` as the per-record version check.

## Data quality behavior

Required columns, timestamps, domain values, uniqueness after deduplication, and referential integrity are validated before Silver output is published. Structural and relational failures fail the batch. Duplicate rows are intentionally resolved by source timestamp and counted in the quality report; they are not misrepresented as invalid source records.

## Storage

DuckDB is a local analytical warehouse and Parquet is used for portable columnar datasets. `CLINICAL_DATA_DIR` relocates source, Bronze, Silver, quality, and warehouse artifacts without changing application code.

## Privacy

All records are generated synthetic data. The project is not designed or approved for PHI or clinical decision support.
