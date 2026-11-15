# Architecture decision records

## ADR-001: DuckDB and Parquet for a local-first portfolio

**Decision:** Use DuckDB for analytical SQL and Parquet for columnar storage.

**Reason:** The project remains reproducible on a developer workstation without a managed database, cloud account, or credentials. The design demonstrates transferable analytical engineering patterns.

## ADR-002: Publish Bronze batches atomically

**Decision:** Write each batch to a staging directory, write a manifest and completion marker, then rename the directory into the published `run_id=...` namespace.

**Reason:** A downstream transformer must not select a partially written batch. The transformer explicitly filters for `_SUCCESS`.

## ADR-003: Compare source versions per business key

**Decision:** Use `source_updated_at` in each MERGE condition to update only when the incoming version is newer.

**Reason:** A global maximum timestamp is unsafe as a filter over complete snapshots: late-arriving changes for an older entity can be missed. The current implementation still reads full snapshots; source-side CDC is a future extension requiring a monotonic change sequence/offset.

## ADR-004: Fail fast on structural and relational defects

**Decision:** Fail the Silver batch for missing required columns, invalid timestamps, invalid domain values, or broken relationships. Deduplicated row counts are reported separately.

**Reason:** Silently dropping invalid clinical-like records would hide data loss. A future quarantine implementation should preserve invalid rows with explicit rejection reasons before selectively allowing a batch to proceed.

## ADR-005: Keep the dashboard read-only

**Decision:** Streamlit opens DuckDB in read-only mode and reads dbt outputs.

**Reason:** Dashboard interactions should not mutate pipeline state or warehouse tables.
