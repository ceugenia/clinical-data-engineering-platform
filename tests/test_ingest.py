import pandas as pd
import pytest

from clinical_pipeline.ingest import ingest_sources


def test_ingestion_creates_bronze_parquet(source_dir, tmp_path):
    counts = ingest_sources(source_dir, tmp_path / "bronze")
    assert counts["patients"] == 240
    run = next((tmp_path / "bronze").glob("run_id=*"))
    frame = pd.read_parquet(run / "patients.parquet")
    assert "ingested_at" in frame.columns
    assert len(frame) == 240


def test_missing_source_fails(tmp_path):
    (tmp_path / "source").mkdir()
    with pytest.raises(FileNotFoundError):
        ingest_sources(tmp_path / "source", tmp_path / "bronze")
