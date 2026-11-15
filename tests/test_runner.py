
import json

import pytest

from clinical_pipeline import runner


def prepare_runner(monkeypatch, tmp_path):
    warehouse_dir = tmp_path / "warehouse"

    def fake_ensure_directories():
        warehouse_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        runner,
        "ensure_directories",
        fake_ensure_directories,
    )

    monkeypatch.setattr(
        runner,
        "WAREHOUSE_DIR",
        warehouse_dir,
    )

    monkeypatch.setattr(
        runner,
        "generate_data",
        lambda seed: None,
    )

    monkeypatch.setattr(
        runner,
        "ingest_sources",
        lambda: {"patients": 10},
    )

    monkeypatch.setattr(
        runner,
        "transform_to_silver",
        lambda: {"patients": 9},
    )

    monkeypatch.setattr(
        runner,
        "apply_incremental_upserts",
        lambda: {
            "status": "success",
            "warehouse": "test.duckdb",
            "tables": {
                "patients": {
                    "incoming": 9,
                    "inserted": 0,
                    "updated": 1,
                    "unchanged": 8,
                    "total_records": 9,
                }
            },
        },
    )

    return warehouse_dir


def read_audit_record(warehouse_dir):
    log_path = warehouse_dir / "pipeline_runs.jsonl"

    lines = log_path.read_text(
        encoding="utf-8"
    ).strip().splitlines()

    return json.loads(lines[-1])


def test_pipeline_records_success(monkeypatch, tmp_path):
    warehouse_dir = prepare_runner(monkeypatch, tmp_path)

    result = runner.run_pipeline(
        generate=True,
        run_dbt=False,
    )

    record = read_audit_record(warehouse_dir)

    assert result["status"] == "success"
    assert record["status"] == "success"
    assert record["run_id"]
    assert record["duration_seconds"] >= 0

    assert record["bronze_row_counts"] == {
        "patients": 10
    }

    assert record["silver_row_counts"] == {
        "patients": 9
    }

    assert record["incremental"]["status"] == "success"

    assert record["incremental"]["tables"]["patients"] == {
        "incoming": 9,
        "inserted": 0,
        "updated": 1,
        "unchanged": 8,
        "total_records": 9,
    }

    assert record["dbt"] == "skipped"
    assert record["failed_stage"] is None
    assert record["error"] is None


def test_pipeline_records_ingestion_failure(monkeypatch, tmp_path):
    warehouse_dir = prepare_runner(monkeypatch, tmp_path)

    def fail_ingestion():
        raise RuntimeError("Test ingestion failure")

    monkeypatch.setattr(
        runner,
        "ingest_sources",
        fail_ingestion,
    )

    with pytest.raises(
        RuntimeError,
        match="Test ingestion failure",
    ):
        runner.run_pipeline(
            generate=True,
            run_dbt=False,
        )

    record = read_audit_record(warehouse_dir)

    assert record["status"] == "failed"
    assert record["failed_stage"] == "ingestion"
    assert record["error"]["type"] == "RuntimeError"
    assert record["error"]["message"] == "Test ingestion failure"
    assert record["incremental"]["status"] == "skipped"


def test_pipeline_records_incremental_failure(
    monkeypatch,
    tmp_path,
):
    warehouse_dir = prepare_runner(monkeypatch, tmp_path)

    def fail_incremental():
        raise ValueError("Test incremental failure")

    monkeypatch.setattr(
        runner,
        "apply_incremental_upserts",
        fail_incremental,
    )

    with pytest.raises(
        ValueError,
        match="Test incremental failure",
    ):
        runner.run_pipeline(
            generate=True,
            run_dbt=False,
        )

    record = read_audit_record(warehouse_dir)

    assert record["status"] == "failed"
    assert record["failed_stage"] == "incremental"
    assert record["incremental"]["status"] == "failed"
    assert record["error"]["type"] == "ValueError"
    assert record["error"]["message"] == "Test incremental failure"


def test_pipeline_can_skip_generation(
    monkeypatch,
    tmp_path,
):
    warehouse_dir = prepare_runner(monkeypatch, tmp_path)

    def unexpected_generation(seed):
        pytest.fail("Data generation should have been skipped.")

    monkeypatch.setattr(
        runner,
        "generate_data",
        unexpected_generation,
    )

    result = runner.run_pipeline(
        generate=False,
        run_dbt=False,
    )

    record = read_audit_record(warehouse_dir)

    assert result["status"] == "success"
    assert record["status"] == "success"
    assert record["incremental"]["status"] == "success"
