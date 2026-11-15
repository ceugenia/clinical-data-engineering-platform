import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from clinical_pipeline.config import BRONZE_DIR, SOURCE_DIR, TABLES


def ingest_sources(
    source_dir: Path = SOURCE_DIR,
    bronze_dir: Path = BRONZE_DIR,
) -> dict[str, int]:
    """Publish a complete, immutable Bronze batch atomically.

    Data is first written to a hidden staging directory. The final run
    directory is made visible only after all Parquet files, the manifest,
    and the completion marker have been written successfully.
    """
    source_dir = Path(source_dir)
    bronze_dir = Path(bronze_dir)
    bronze_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("%Y%m%dT%H%M%S%fZ")
    staging_dir = bronze_dir / f".staging_run_id={run_id}"
    final_dir = bronze_dir / f"run_id={run_id}"
    staging_dir.mkdir(parents=False, exist_ok=False)

    counts: dict[str, int] = {}
    manifest = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "completed_at": None,
        "status": "in_progress",
        "tables": {},
    }

    try:
        for table in TABLES:
            source = source_dir / f"{table}.csv"
            if not source.is_file():
                raise FileNotFoundError(
                    f"Missing source file: {source}. Generate source data first."
                )

            frame = pd.read_csv(source)
            frame["ingested_at"] = datetime.now(timezone.utc).isoformat()
            frame["source_file"] = source.name
            output = staging_dir / f"{table}.parquet"
            frame.to_parquet(output, index=False)

            counts[table] = len(frame)
            manifest["tables"][table] = {
                "source_file": source.name,
                "row_count": len(frame),
                "parquet_file": output.name,
            }

        manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
        manifest["status"] = "success"

        (staging_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        # Completion marker is written last inside the staging directory.
        (staging_dir / "_SUCCESS").write_text(
            manifest["completed_at"],
            encoding="utf-8",
        )

        # Atomic directory rename on the same filesystem.
        staging_dir.replace(final_dir)
        return counts

    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
