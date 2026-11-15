# Architecture and design decisions

## Medallion architecture
Bronze preserves timestamped source snapshots. Silver standardizes and validates entities. Gold contains business-facing dbt models. This separation helps isolate source defects from transformation and business-logic defects.

## DuckDB and Parquet
DuckDB is an analytical SQL engine that runs locally without a database server. Parquet is columnar and supported across modern analytical platforms. This combination makes the demo reproducible while using transferable data-platform patterns.

## Repeatability and future incremental strategy
Each ingestion writes an immutable Bronze snapshot. The demo transforms the latest snapshot into deterministic Silver tables, deduplicating on business keys. dbt rebuilds Gold tables from Silver. A production extension could use source change timestamps and merge/upsert logic to process only changed records.

## Quality and privacy
Python checks required fields, valid domains, uniqueness through deduplication, and referential integrity. dbt adds uniqueness, not-null, relationship, and business-rule tests. Every record is synthetic; no direct identifiers or real patient information are included.
