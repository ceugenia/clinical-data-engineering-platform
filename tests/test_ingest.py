import json

import pandas as pd
import pytest

from clinical_pipeline.ingest import ingest_sources


def test_ingestion_creates_complete_bronze_batch(source_dir, tmp_path):
    bronze_dir = tmp_path / "bronze"
    counts = ingest_sources(source_dir, bronze_dir)

    assert counts["patients"] == 240
    runs = list(bronze_dir.glob("run_id=*"))
    assert len(runs) == 1

    run = runs[0]
    assert (run / "_SUCCESS").is_file()
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "success"
    assert manifest["tables"]["patients"]["row_count"] == 240

    frame = pd.read_parquet(run / "patients.parquet")
    assert "ingested_at" in frame.columns
    assert len(frame) == 240
    assert not list(bronze_dir.glob(".staging_run_id=*"))


def test_missing_source_fails_without_publishing_partial_batch(tmp_path):
    source_dir = tmp_path / "source"
    bronze_dir = tmp_path / "bronze"
    source_dir.mkdir()
    pd.DataFrame({"trial_id": ["TR-1"]}).to_csv(
        source_dir / "trials.csv", index=False
    )

    with pytest.raises(FileNotFoundError):
        ingest_sources(source_dir, bronze_dir)

    assert not list(bronze_dir.glob("run_id=*"))
    assert not list(bronze_dir.glob(".staging_run_id=*"))
