
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from clinical_pipeline.config import TABLES
from clinical_pipeline.incremental import (
    PRIMARY_KEYS,
    apply_incremental_upserts,
)


BASE_TIMESTAMP = "2026-01-01T00:00:00+00:00"
NEW_TIMESTAMP = "2026-01-02T00:00:00+00:00"
OLDER_TIMESTAMP = "2025-12-31T00:00:00+00:00"


def write_silver_snapshot(
    silver_dir: Path,
    overrides: dict | None = None,
) -> None:
    """Create small Silver Parquet datasets for testing."""

    silver_dir.mkdir(parents=True, exist_ok=True)
    overrides = overrides or {}

    record_ids = {
        "patients": "PT-00001",
        "trials": "TR-00001",
        "visits": "PT-00001-V1",
        "lab_results": "LAB-00001",
    }

    for table in TABLES:
        key = PRIMARY_KEYS[table]

        records = overrides.get(
            table,
            [
                {
                    key: record_ids[table],
                    "record_value": "baseline",
                    "source_updated_at": BASE_TIMESTAMP,
                }
            ],
        )

        frame = pd.DataFrame(records)

        frame.to_parquet(
            silver_dir / f"{table}.parquet",
            index=False,
        )


def read_warehouse_record(
    db_path: Path,
    table: str,
    key: str,
    record_id: str,
) -> dict:
    """Read one record from a persistent DuckDB table."""

    connection = duckdb.connect(
        str(db_path),
        read_only=True,
    )

    try:
        row = connection.execute(
            f"""
            SELECT *
            FROM silver_{table}
            WHERE {key} = ?
            """,
            [record_id],
        ).fetchdf()

        assert len(row) == 1

        return row.iloc[0].to_dict()

    finally:
        connection.close()


def test_initial_load_inserts_all_records(tmp_path):
    silver_dir = tmp_path / "silver"
    db_path = tmp_path / "warehouse" / "clinical.duckdb"

    write_silver_snapshot(silver_dir)

    result = apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    assert result["status"] == "success"

    for table in TABLES:
        table_result = result["tables"][table]

        assert table_result["incoming"] == 1
        assert table_result["inserted"] == 1
        assert table_result["updated"] == 0
        assert table_result["unchanged"] == 0
        assert table_result["total_records"] == 1


def test_second_load_is_idempotent(tmp_path):
    silver_dir = tmp_path / "silver"
    db_path = tmp_path / "warehouse" / "clinical.duckdb"

    write_silver_snapshot(silver_dir)

    apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    result = apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    for table in TABLES:
        table_result = result["tables"][table]

        assert table_result["inserted"] == 0
        assert table_result["updated"] == 0
        assert table_result["unchanged"] == 1
        assert table_result["total_records"] == 1


def test_newer_timestamp_updates_existing_record(tmp_path):
    silver_dir = tmp_path / "silver"
    db_path = tmp_path / "warehouse" / "clinical.duckdb"

    write_silver_snapshot(silver_dir)

    apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    updated_patient = {
        "patient_id": "PT-00001",
        "record_value": "updated",
        "source_updated_at": NEW_TIMESTAMP,
    }

    write_silver_snapshot(
        silver_dir,
        overrides={
            "patients": [updated_patient],
        },
    )

    result = apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    patient_result = result["tables"]["patients"]

    assert patient_result["inserted"] == 0
    assert patient_result["updated"] == 1
    assert patient_result["unchanged"] == 0
    assert patient_result["total_records"] == 1

    patient = read_warehouse_record(
        db_path,
        "patients",
        "patient_id",
        "PT-00001",
    )

    assert patient["record_value"] == "updated"
    assert pd.Timestamp(
        patient["source_updated_at"]
    ) == pd.Timestamp(NEW_TIMESTAMP)


def test_older_timestamp_does_not_overwrite_newer_record(tmp_path):
    silver_dir = tmp_path / "silver"
    db_path = tmp_path / "warehouse" / "clinical.duckdb"

    write_silver_snapshot(
        silver_dir,
        overrides={
            "patients": [
                {
                    "patient_id": "PT-00001",
                    "record_value": "newest",
                    "source_updated_at": NEW_TIMESTAMP,
                }
            ]
        },
    )

    apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    write_silver_snapshot(
        silver_dir,
        overrides={
            "patients": [
                {
                    "patient_id": "PT-00001",
                    "record_value": "older",
                    "source_updated_at": OLDER_TIMESTAMP,
                }
            ]
        },
    )

    result = apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    patient_result = result["tables"]["patients"]

    assert patient_result["inserted"] == 0
    assert patient_result["updated"] == 0
    assert patient_result["unchanged"] == 1

    patient = read_warehouse_record(
        db_path,
        "patients",
        "patient_id",
        "PT-00001",
    )

    assert patient["record_value"] == "newest"
    assert pd.Timestamp(
        patient["source_updated_at"]
    ) == pd.Timestamp(NEW_TIMESTAMP)


def test_duplicate_business_keys_are_rejected(tmp_path):
    silver_dir = tmp_path / "silver"
    db_path = tmp_path / "warehouse" / "clinical.duckdb"

    write_silver_snapshot(silver_dir)

    duplicate_patients = [
        {
            "patient_id": "PT-00001",
            "record_value": "first",
            "source_updated_at": BASE_TIMESTAMP,
        },
        {
            "patient_id": "PT-00001",
            "record_value": "duplicate",
            "source_updated_at": NEW_TIMESTAMP,
        },
    ]

    write_silver_snapshot(
        silver_dir,
        overrides={
            "patients": duplicate_patients,
        },
    )

    with pytest.raises(
        ValueError,
        match="missing or duplicate business keys",
    ):
        apply_incremental_upserts(
            silver_dir=silver_dir,
            db_path=db_path,
        )


def test_invalid_timestamp_rolls_back_transaction(tmp_path):
    silver_dir = tmp_path / "silver"
    db_path = tmp_path / "warehouse" / "clinical.duckdb"

    write_silver_snapshot(silver_dir)

    apply_incremental_upserts(
        silver_dir=silver_dir,
        db_path=db_path,
    )

    updated_patient = {
        "patient_id": "PT-00001",
        "record_value": "should_not_commit",
        "source_updated_at": NEW_TIMESTAMP,
    }

    invalid_lab = {
        "lab_result_id": "LAB-00001",
        "record_value": "invalid",
        "source_updated_at": "not-a-valid-timestamp",
    }

    write_silver_snapshot(
        silver_dir,
        overrides={
            "patients": [updated_patient],
            "lab_results": [invalid_lab],
        },
    )

    with pytest.raises(
        ValueError,
        match="invalid source update timestamps",
    ):
        apply_incremental_upserts(
            silver_dir=silver_dir,
            db_path=db_path,
        )

    patient = read_warehouse_record(
        db_path,
        "patients",
        "patient_id",
        "PT-00001",
    )

    # The patient update must not have been committed.
    assert patient["record_value"] == "baseline"
    assert pd.Timestamp(
        patient["source_updated_at"]
    ) == pd.Timestamp(BASE_TIMESTAMP)
