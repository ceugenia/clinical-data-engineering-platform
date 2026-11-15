
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone

from clinical_pipeline.config import (
    DB_PATH,
    DBT_DIR,
    SILVER_DIR,
    WAREHOUSE_DIR,
    ensure_directories,
)
from clinical_pipeline.generate import generate_data
from clinical_pipeline.ingest import ingest_sources
from clinical_pipeline.incremental import apply_incremental_upserts
from clinical_pipeline.transform import transform_to_silver


def _write_audit_log(record: dict[str, object]) -> None:
    """Append one pipeline execution record to the JSONL audit log."""
    log_path = WAREHOUSE_DIR / "pipeline_runs.jsonl"

    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


def run_pipeline(
    generate: bool = True,
    run_dbt: bool = True,
    seed: int = 42,
) -> dict[str, object]:
    """Execute the clinical data pipeline and record execution metrics."""

    ensure_directories()

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    start_timer = time.perf_counter()

    bronze = {}
    silver = {}
    incremental = {"status": "skipped"}
    dbt_status = "skipped"

    status = "failed"
    error = None
    current_stage = "initialization"

    try:
        # Step 1: Generate synthetic source data when requested.
        if generate:
            current_stage = "generation"
            generate_data(seed=seed)

        # Step 2: Ingest source CSV files into Bronze.
        current_stage = "ingestion"
        bronze = ingest_sources()

        # Step 3: Transform and validate Bronze data into Silver.
        current_stage = "transformation"
        silver = transform_to_silver()

        # Step 4: Upsert Silver records into DuckDB.
        current_stage = "incremental"
        incremental = apply_incremental_upserts()

        # Step 5: Run dbt models and data quality tests.
        if run_dbt:
            current_stage = "dbt"

            env = os.environ.copy()
            env["CLINICAL_DUCKDB_PATH"] = str(DB_PATH)

            dbt_executable = shutil.which("dbt")

            if dbt_executable is None:
                raise RuntimeError(
                    "dbt executable not found. Install dbt-duckdb "
                    "in your active virtual environment."
                )

            subprocess.run(
                [
                    dbt_executable,
                    "build",
                    "--project-dir",
                    str(DBT_DIR),
                    "--profiles-dir",
                    str(DBT_DIR),
                    "--vars",
                    json.dumps({
                        "silver_dir": str(SILVER_DIR).replace("\\", "/")
                    }),
                ],
                check=True,
                cwd=DBT_DIR.parent,
                env=env,
            )

            dbt_status = "passed"

        status = "success"
        current_stage = "completed"

    except Exception as exc:
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }

        if current_stage == "incremental":
            incremental = {"status": "failed"}

        raise

    finally:
        finished_at = datetime.now(timezone.utc)

        audit_record = {
            "run_id": run_id,
            "status": status,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(
                time.perf_counter() - start_timer, 3
            ),
            "bronze_row_counts": bronze,
            "silver_row_counts": silver,
            "incremental": incremental,
            "dbt": dbt_status,
            "warehouse": str(DB_PATH),
            "failed_stage": (
                current_stage if status == "failed" else None
            ),
            "error": error,
        }

        _write_audit_log(audit_record)

    return audit_record
