
from pathlib import Path

import pandas as pd

from clinical_pipeline.config import SOURCE_DIR


BASE_TIMESTAMP = "2026-01-01T00:00:00+00:00"
CHANGE_TIMESTAMP = "2026-01-02T00:00:00+00:00"


def simulate_source_changes(source_dir: Path = SOURCE_DIR) -> dict[str, int]:
    """Simulate updates arriving from clinical source systems."""

    changes = {
        "patients": "PT-00001",
        "visits": None,
        "lab_results": None,
    }

    updated_counts = {}

    for table in ("patients", "visits", "lab_results"):
        path = source_dir / f"{table}.csv"

        if not path.exists():
            raise FileNotFoundError(f"Missing source file: {path}")

        frame = pd.read_csv(path)

        if "source_updated_at" not in frame.columns:
            raise ValueError(
                f"{table} does not contain source_updated_at. "
                "Regenerate the source data first."
            )

        if not frame["source_updated_at"].eq(BASE_TIMESTAMP).all():
            raise ValueError(
                f"{table} has already been modified. "
                "Regenerate the baseline before simulating again."
            )

        if frame.empty:
            raise ValueError(f"{table} contains no records.")

        if table == "patients":
            mask = frame["patient_id"].eq("PT-00001")
            if not mask.any():
                raise ValueError("Patient PT-00001 was not found.")
            frame.loc[mask, "enrollment_status"] = "Withdrawn"

        elif table == "visits":
            frame.loc[0, "visit_status"] = "Missed"

        elif table == "lab_results":
            frame.loc[0, "result_value"] = round(
                float(frame.loc[0, "result_value"]) + 1.0, 2
            )

        frame.loc[
            (mask if table == "patients" else frame.index == frame.index[0]),
            "source_updated_at",
        ] = CHANGE_TIMESTAMP

        frame.to_csv(path, index=False)
        updated_counts[table] = 1

    return updated_counts


if __name__ == "__main__":
    counts = simulate_source_changes()
    print(f"Simulated source changes: {counts}")
