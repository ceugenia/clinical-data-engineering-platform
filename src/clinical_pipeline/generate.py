from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from clinical_pipeline.config import SOURCE_DIR


def generate_data(output_dir: Path = SOURCE_DIR, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Create deterministic, entirely synthetic clinical operations data."""
    rng = np.random.default_rng(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    trials = pd.DataFrame([
        {"trial_id": "TR-1001", "trial_name": "ORBIT", "therapeutic_area": "Oncology", "phase": "Phase II", "site_count": 8},
        {"trial_id": "TR-1002", "trial_name": "NOVA", "therapeutic_area": "Immunology", "phase": "Phase III", "site_count": 12},
        {"trial_id": "TR-1003", "trial_name": "PULSE", "therapeutic_area": "Cardiology", "phase": "Phase I", "site_count": 5},
        {"trial_id": "TR-1004", "trial_name": "ATLAS", "therapeutic_area": "Neurology", "phase": "Phase II", "site_count": 7},
    ])
    n = 240
    ids = [f"PT-{i:05d}" for i in range(1, n + 1)]
    trial_ids = rng.choice(trials.trial_id, size=n, p=[.30, .32, .18, .20])
    base = date(2025, 1, 1)
    offsets = rng.integers(0, 500, size=n)
    patients = pd.DataFrame({
        "patient_id": ids, "trial_id": trial_ids,
        "site_id": [f"SITE-{int(x):02d}" for x in rng.integers(1, 13, size=n)],
        "enrollment_date": [(base + timedelta(days=int(x))).isoformat() for x in offsets],
        "age": rng.integers(18, 86, size=n),
        "sex": rng.choice(["Female", "Male", "Unknown"], size=n, p=[.49, .48, .03]),
        "enrollment_status": rng.choice(
            ["Screening", "Enrolled", "Withdrawn", "Completed"], size=n,
            p=[.08, .66, .10, .16]),
    })
    visits_list = []
    visit_types = ["Screening", "Baseline", "Week 4", "Week 8", "Week 12"]
    for p in patients.itertuples(index=False):
        enrolled = date.fromisoformat(p.enrollment_date)
        for number, kind in enumerate(visit_types, 1):
            day = enrolled + timedelta(days=(number - 1) * 28 + int(rng.integers(-2, 3)))
            status = rng.choice(["Completed", "Scheduled", "Missed", "Cancelled"],
                                p=[.72, .15, .08, .05])
            visits_list.append({
                "visit_id": f"{p.patient_id}-V{number}", "patient_id": p.patient_id,
                "trial_id": p.trial_id, "visit_number": number, "visit_type": kind,
                "visit_date": day.isoformat(), "visit_status": status,
            })
    visits = pd.DataFrame(visits_list)
    analytes = {
        "ALT": ("U/L", 7., 56., 25., 12.),
        "AST": ("U/L", 10., 40., 22., 10.),
        "CRP": ("mg/L", 0., 10., 5., 4.),
        "Hemoglobin": ("g/dL", 12., 17.5, 14., 1.5),
    }
    labs_list = []
    completed = visits.loc[visits.visit_status == "Completed"]
    for v in completed.sample(frac=.55, random_state=seed).itertuples(index=False):
        for analyte, (unit, low, high, mean, sd) in analytes.items():
            labs_list.append({
                "lab_result_id": f"{v.visit_id}-{analyte.lower()}",
                "patient_id": v.patient_id, "trial_id": v.trial_id,
                "visit_id": v.visit_id, "collection_date": v.visit_date,
                "analyte": analyte, "result_value": round(max(.1, float(rng.normal(mean, sd))), 2),
                "unit": unit, "reference_low": low, "reference_high": high,
            })
    labs = pd.DataFrame(labs_list)
    # Intentional duplicate records allow the deduplication logic to be demonstrated.
    visits = pd.concat([visits, visits.iloc[[0]]], ignore_index=True)
    labs = pd.concat([labs, labs.iloc[[0]]], ignore_index=True)
    
    result = {
        "patients": patients,
        "trials": trials,
        "visits": visits,
        "lab_results": labs,
    }

    # Deterministic baseline timestamp for the synthetic source records.
    source_updated_at = "2026-01-01T00:00:00+00:00"

    for name, frame in result.items():
        frame["source_updated_at"] = source_updated_at
        frame.to_csv(output_dir / f"{name}.csv", index=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    generate_data(seed=parser.parse_args().seed)
