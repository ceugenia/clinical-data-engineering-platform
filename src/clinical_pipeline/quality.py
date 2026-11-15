import json
from datetime import datetime, timezone
from pathlib import Path

from clinical_pipeline.config import QUALITY_REPORT_PATH


def write_quality_report(
    table_metrics: dict[str, dict[str, int]],
    report_path: Path = QUALITY_REPORT_PATH,
) -> dict[str, object]:
    """Write a machine-readable report for successful Silver validation.

    Duplicate source rows are reported as deduplicated rows, not silently
    described as invalid records. Structural and referential failures remain
    fail-fast in the transformation step.
    """
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    checks = [
        {"name": "required_columns_present", "status": "passed"},
        {"name": "source_timestamps_valid", "status": "passed"},
        {"name": "business_keys_unique_after_deduplication", "status": "passed"},
        {"name": "domain_values_valid", "status": "passed"},
        {"name": "referential_integrity", "status": "passed"},
    ]

    report: dict[str, object] = {
        "status": "passed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "tables": table_metrics,
        "totals": {
            "source_rows": sum(v["source_rows"] for v in table_metrics.values()),
            "silver_rows": sum(v["silver_rows"] for v in table_metrics.values()),
            "deduplicated_rows": sum(
                v["deduplicated_rows"] for v in table_metrics.values()
            ),
        },
        "rejected_rows": 0,
        "note": (
            "Invalid structural or referential data fails the batch. "
            "Duplicate source rows are counted separately as deduplicated rows."
        ),
    }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
