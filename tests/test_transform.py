import pandas as pd
import pytest

from clinical_pipeline.ingest import ingest_sources
from clinical_pipeline.transform import transform_to_silver


def test_silver_deduplicates(source_dir, tmp_path):
    bronze, silver = tmp_path / "bronze", tmp_path / "silver"
    ingest_sources(source_dir, bronze)
    counts = transform_to_silver(bronze, silver)
    assert counts["patients"] == 240
    assert counts["visits"] == 1200
    assert pd.read_parquet(silver / "patients.parquet").patient_id.is_unique
    assert pd.read_parquet(silver / "visits.parquet").visit_id.is_unique


def test_invalid_age_fails(source_dir, tmp_path):
    patients = pd.read_csv(source_dir / "patients.csv")
    patients.loc[0, "age"] = 5
    patients.to_csv(source_dir / "patients.csv", index=False)
    bronze = tmp_path / "bronze"
    ingest_sources(source_dir, bronze)
    with pytest.raises(ValueError, match="ages"):
        transform_to_silver(bronze, tmp_path / "silver")
