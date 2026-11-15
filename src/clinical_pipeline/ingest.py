from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from clinical_pipeline.config import BRONZE_DIR, SOURCE_DIR, TABLES, ensure_directories


def ingest_sources(source_dir: Path = SOURCE_DIR, bronze_dir: Path = BRONZE_DIR) -> dict[str, int]:
    """Load source CSV files and persist timestamped Bronze Parquet snapshots."""
    ensure_directories()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = bronze_dir / f"run_id={run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for table in TABLES:
        source = source_dir / f"{table}.csv"
        if not source.exists():
            raise FileNotFoundError(f"Missing {source}; generate source data first.")
        frame = pd.read_csv(source)
        frame["ingested_at"] = datetime.now(timezone.utc).isoformat()
        frame["source_file"] = source.name
        frame.to_parquet(run_dir / f"{table}.parquet", index=False)
        counts[table] = len(frame)
    return counts
