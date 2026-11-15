import json

from clinical_pipeline.quality import write_quality_report


def test_quality_report_records_row_metrics(tmp_path):
    report_path = tmp_path / "quality" / "quality_report.json"
    metrics = {
        "patients": {
            "source_rows": 10,
            "silver_rows": 9,
            "deduplicated_rows": 1,
        }
    }

    report = write_quality_report(metrics, report_path)

    saved = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert saved["totals"] == {
        "source_rows": 10,
        "silver_rows": 9,
        "deduplicated_rows": 1,
    }
    assert saved["rejected_rows"] == 0
