
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
    """Execute the clinical data pipeline and record success or failure."""
    ensure_directories()

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    start_timer = time.perf_counter()

    bronze = {}
    silver = {}
    dbt_status = "skipped"

    try:
        if generate:
            generate_data(seed=seed)

        bronze = ingest_sources()
        silver = transform_to_silver()

        if run_dbt:
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
        error = None

    except Exception as exc:
        status = "failed"
        error = {
            "type": type(exc).__name__,
            "message": str(exc),
        }
        raise

    finally:
        finished_at = datetime.now(timezone.utc)

        audit_record = {
            "run_id": run_id,
            "status": status if "status" in locals() else "failed",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(
                time.perf_counter() - start_timer, 3
            ),
            "bronze_row_counts": bronze,
            "silver_row_counts": silver,
            "dbt": dbt_status,
            "warehouse": str(DB_PATH),
            "error": error if "error" in locals() else {
                "type": "UnknownError",
                "message": "Pipeline ended unexpectedly.",
            },
        }

        _write_audit_log(audit_record)

    return audit_record
