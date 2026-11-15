
import json

import pytest

from clinical_pipeline import runner


def prepare_runner(monkeypatch, tmp_path):
    warehouse_dir = tmp_path / "warehouse"

    def fake_ensure_directories():
        warehouse_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(runner, "ensure_directories", fake_ensure_directories)
    monkeypatch.setattr(runner, "WAREHOUSE_DIR", warehouse_dir)
    monkeypatch.setattr(runner, "generate_data", lambda seed: None)
    monkeypatch.setattr(
        runner, "ingest_sources", lambda: {"patients": 10}
    )
    monkeypatch.setattr(
        runner, "transform_to_silver", lambda: {"patients": 9}
    )

    return warehouse_dir


def test_pipeline_records_success(monkeypatch, tmp_path):
    warehouse_dir = prepare_runner(monkeypatch, tmp_path)

    result = runner.run_pipeline(generate=True, run_dbt=False)

    log_path = warehouse_dir / "pipeline_runs.jsonl"
    record = json.loads(log_path.read_text(encoding="utf-8"))

    assert result["status"] == "success"
    assert record["status"] == "success"
    assert record["run_id"]
    assert record["duration_seconds"] >= 0
    assert record["bronze_row_counts"] == {"patients": 10}
    assert record["silver_row_counts"] == {"patients": 9}
    assert record["dbt"] == "skipped"
    assert record["error"] is None


def test_pipeline_records_failure(monkeypatch, tmp_path):
    warehouse_dir = prepare_runner(monkeypatch, tmp_path)

    def fail_ingestion():
        raise RuntimeError("Test ingestion failure")

    monkeypatch.setattr(runner, "ingest_sources", fail_ingestion)

    with pytest.raises(RuntimeError, match="Test ingestion failure"):
        runner.run_pipeline(generate=True, run_dbt=False)

    log_path = warehouse_dir / "pipeline_runs.jsonl"
    record = json.loads(log_path.read_text(encoding="utf-8"))

    assert record["status"] == "failed"
    assert record["error"]["type"] == "RuntimeError"
    assert record["error"]["message"] == "Test ingestion failure"
