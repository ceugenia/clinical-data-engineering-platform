
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from clinical_pipeline.config import (
    DB_PATH,
    SILVER_DIR,
    TABLES,
)


PRIMARY_KEYS = {
    "patients": "patient_id",
    "trials": "trial_id",
    "visits": "visit_id",
    "lab_results": "lab_result_id",
}


def _table_name(table: str) -> str:
    """Return the DuckDB target table name."""
    return f"silver_{table}"


def _upsert_table(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    frame: pd.DataFrame,
) -> dict[str, int]:
    """
    Insert new records and update existing records
    when their source update timestamp is newer.
    """

    key = PRIMARY_KEYS[table]
    target = _table_name(table)
    staging = f"incoming_{table}"

    if "source_updated_at" not in frame.columns:
        raise ValueError(
            f"{table} is missing source_updated_at."
        )

    if frame[key].isna().any() or frame[key].duplicated().any():
        raise ValueError(
            f"{table} contains missing or duplicate business keys."
        )

    frame = frame.copy()

    # Normalize source timestamps to UTC.
    frame["source_updated_at"] = pd.to_datetime(
        frame["source_updated_at"],
        errors="coerce",
        utc=True,
    )

    if frame["source_updated_at"].isna().any():
        raise ValueError(
            f"{table} contains invalid source update timestamps."
        )

    connection.register(staging, frame)

    try:
        # Create the target table if it does not exist.
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {target} AS
            SELECT *
            FROM {staging}
            WHERE 1 = 0
            """
        )

        # Count new records.
        inserted = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {staging} AS source
            LEFT JOIN {target} AS target
                ON source.{key} = target.{key}
            WHERE target.{key} IS NULL
            """
        ).fetchone()[0]

        # Count records with newer source timestamps.
        updated = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {staging} AS source
            INNER JOIN {target} AS target
                ON source.{key} = target.{key}
            WHERE source.source_updated_at >
                  target.source_updated_at
            """
        ).fetchone()[0]

        columns = list(frame.columns)

        update_assignments = ", ".join(
            f"{column} = source.{column}"
            for column in columns
            if column != key
        )

        column_list = ", ".join(columns)

        value_list = ", ".join(
            f"source.{column}"
            for column in columns
        )

        # Perform the upsert.
        connection.execute(
            f"""
            MERGE INTO {target} AS target
            USING {staging} AS source
                ON target.{key} = source.{key}

            WHEN MATCHED
                AND source.source_updated_at >
                    target.source_updated_at
            THEN UPDATE SET
                {update_assignments}

            WHEN NOT MATCHED
            THEN INSERT ({column_list})
                 VALUES ({value_list})
            """
        )

        total = len(frame)

        return {
            "incoming": total,
            "inserted": inserted,
            "updated": updated,
            "unchanged": total - inserted - updated,
            "total_records": connection.execute(
                f"SELECT COUNT(*) FROM {target}"
            ).fetchone()[0],
        }

    finally:
        connection.unregister(staging)


def apply_incremental_upserts(
    silver_dir: Path = SILVER_DIR,
    db_path: Path = DB_PATH,
) -> dict[str, object]:
    """
    Incrementally upsert validated Silver Parquet records into DuckDB.

    Records are inserted when new and updated only when their
    source_updated_at timestamp is newer than the stored timestamp.
    """

    silver_dir = Path(silver_dir)
    db_path = Path(db_path)

    if not silver_dir.exists():
        raise FileNotFoundError(
            f"Silver directory does not exist: {silver_dir}"
        )

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    results = {}

    connection = duckdb.connect(str(db_path))

    try:
        connection.execute("BEGIN TRANSACTION")

        # Create incremental processing metadata.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS incremental_watermarks (
                table_name VARCHAR PRIMARY KEY,
                max_source_updated_at TIMESTAMPTZ,
                last_processed_at TIMESTAMPTZ,
                inserted_rows BIGINT,
                updated_rows BIGINT
            )
            """
        )

        # Process all datasets in one transaction.
        for table in TABLES:
            parquet_path = silver_dir / f"{table}.parquet"

            if not parquet_path.exists():
                raise FileNotFoundError(
                    f"Missing Silver dataset: {parquet_path}"
                )

            frame = pd.read_parquet(parquet_path)

            result = _upsert_table(
                connection=connection,
                table=table,
                frame=frame,
            )

            results[table] = result

            # Normalize timestamps before calculating the watermark.
            # This handles both string and datetime Parquet columns.
            source_timestamps = pd.to_datetime(
                frame["source_updated_at"],
                errors="coerce",
                utc=True,
            )

            max_timestamp = source_timestamps.max()

            if pd.isna(max_timestamp):
                raise ValueError(
                    f"{table} contains no valid source update timestamps."
                )

            processed_at = datetime.now(timezone.utc)

            # Store the latest source timestamp and processing metrics.
            connection.execute(
                """
                INSERT INTO incremental_watermarks (
                    table_name,
                    max_source_updated_at,
                    last_processed_at,
                    inserted_rows,
                    updated_rows
                )
                VALUES (?, ?, ?, ?, ?)

                ON CONFLICT (table_name)
                DO UPDATE SET
                    max_source_updated_at =
                        excluded.max_source_updated_at,
                    last_processed_at =
                        excluded.last_processed_at,
                    inserted_rows =
                        excluded.inserted_rows,
                    updated_rows =
                        excluded.updated_rows
                """,
                [
                    table,
                    max_timestamp.to_pydatetime(),
                    processed_at,
                    result["inserted"],
                    result["updated"],
                ],
            )

        # Commit all DuckDB changes.
        connection.execute("COMMIT")

        # Export complete merged DuckDB tables back to Silver Parquet.
        for table in TABLES:
            target = _table_name(table)

            merged_frame = connection.execute(
                f"SELECT * FROM {target}"
            ).fetchdf()

            output_path = silver_dir / f"{table}.parquet"
            temporary_path = silver_dir / f"{table}.tmp.parquet"

            merged_frame.to_parquet(
                temporary_path,
                index=False,
            )

            temporary_path.replace(output_path)

    except Exception:
        try:
            connection.execute("ROLLBACK")
        except duckdb.Error:
            pass

        raise

    finally:
        connection.close()

    return {
        "status": "success",
        "warehouse": str(db_path),
        "tables": results,
    }
