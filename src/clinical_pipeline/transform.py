
from pathlib import Path

import pandas as pd

from clinical_pipeline.config import (
    BRONZE_DIR,
    SILVER_DIR,
    TABLES,
    ensure_directories,
)


REQUIRED = {
    "patients": {
        "patient_id",
        "trial_id",
        "enrollment_date",
        "age",
        "enrollment_status",
        "source_updated_at",
    },
    "trials": {
        "trial_id",
        "trial_name",
        "therapeutic_area",
        "phase",
        "source_updated_at",
    },
    "visits": {
        "visit_id",
        "patient_id",
        "trial_id",
        "visit_date",
        "visit_status",
        "source_updated_at",
    },
    "lab_results": {
        "lab_result_id",
        "patient_id",
        "trial_id",
        "visit_id",
        "analyte",
        "result_value",
        "source_updated_at",
    },
}


PRIMARY_KEYS = {
    "patients": "patient_id",
    "trials": "trial_id",
    "visits": "visit_id",
    "lab_results": "lab_result_id",
}


def keep_latest_record(
    frame: pd.DataFrame,
    key: str,
) -> pd.DataFrame:
    """
    Deduplicate records by business key.

    Keep the record with the newest source_updated_at timestamp.
    When timestamps are identical, keep the last occurrence.
    """

    return (
        frame.sort_values(
            by="source_updated_at",
            ascending=True,
            kind="stable",
        )
        .drop_duplicates(
            subset=[key],
            keep="last",
        )
        .copy()
        .reset_index(drop=True)
    )


def transform_to_silver(
    bronze_dir: Path = BRONZE_DIR,
    silver_dir: Path = SILVER_DIR,
) -> dict[str, int]:
    """Validate, deduplicate, and standardize the latest Bronze snapshot."""

    ensure_directories()

    bronze_dir = Path(bronze_dir)
    silver_dir = Path(silver_dir)

    runs = sorted(bronze_dir.glob("run_id=*"))

    if not runs:
        raise FileNotFoundError(
            "No Bronze snapshot found; run ingestion first."
        )

    frames = {}

    # Load and validate Bronze datasets.
    for table in TABLES:
        frame = pd.read_parquet(
            runs[-1] / f"{table}.parquet"
        )

        missing = REQUIRED[table] - set(frame.columns)

        if missing:
            raise ValueError(
                f"{table} missing required columns: {sorted(missing)}"
            )

        # Validate source update timestamps.
        frame["source_updated_at"] = pd.to_datetime(
            frame["source_updated_at"],
            errors="coerce",
            utc=True,
        )

        if frame["source_updated_at"].isna().any():
            raise ValueError(
                f"{table} contains missing or invalid "
                "source update timestamps."
            )

        frames[table] = frame

    # Deduplicate using business keys and newest source timestamps.
    patients = keep_latest_record(
        frames["patients"],
        PRIMARY_KEYS["patients"],
    )

    trials = keep_latest_record(
        frames["trials"],
        PRIMARY_KEYS["trials"],
    )

    visits = keep_latest_record(
        frames["visits"],
        PRIMARY_KEYS["visits"],
    )

    labs = keep_latest_record(
        frames["lab_results"],
        PRIMARY_KEYS["lab_results"],
    )

    # Standardize data types and values.
    patients["enrollment_date"] = pd.to_datetime(
        patients["enrollment_date"],
        errors="coerce",
    )

    patients["age"] = pd.to_numeric(
        patients["age"],
        errors="coerce",
    ).astype("Int64")

    visits["visit_date"] = pd.to_datetime(
        visits["visit_date"],
        errors="coerce",
    )

    labs["collection_date"] = pd.to_datetime(
        labs["collection_date"],
        errors="coerce",
    )

    labs["result_value"] = pd.to_numeric(
        labs["result_value"],
        errors="coerce",
    )

    patients["enrollment_status"] = (
        patients["enrollment_status"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    visits["visit_status"] = (
        visits["visit_status"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    labs["analyte"] = (
        labs["analyte"]
        .astype("string")
        .str.strip()
    )

    # Validate trial records.
    if (
        trials["trial_id"].isna().any()
        or trials["trial_id"].duplicated().any()
    ):
        raise ValueError(
            "Trial identifiers must be present and unique."
        )

    # Validate patient records.
    if patients[
        ["patient_id", "trial_id", "enrollment_date"]
    ].isna().any().any():
        raise ValueError(
            "Patient identifiers, trial IDs, and enrollment dates "
            "cannot be null."
        )

    if patients["patient_id"].duplicated().any():
        raise ValueError(
            "Patient identifiers must be unique after deduplication."
        )

    if (
        patients["age"].isna().any()
        or not patients["age"].between(18, 100).all()
    ):
        raise ValueError(
            "Patient ages must be between 18 and 100."
        )

    valid_enrollment_statuses = {
        "Screening",
        "Enrolled",
        "Withdrawn",
        "Completed",
    }

    if not patients["enrollment_status"].isin(
        valid_enrollment_statuses
    ).all():
        raise ValueError(
            "Unexpected enrollment status."
        )

    # Validate visit records.
    if visits[
        ["visit_id", "patient_id", "trial_id", "visit_date"]
    ].isna().any().any():
        raise ValueError(
            "Visit identifiers, relationships, and dates cannot be null."
        )

    valid_visit_statuses = {
        "Completed",
        "Scheduled",
        "Missed",
        "Cancelled",
    }

    if (
        visits["visit_status"].isna().any()
        or not visits["visit_status"].isin(
            valid_visit_statuses
        ).all()
    ):
        raise ValueError(
            "Unexpected or null visit status."
        )

    # Validate patient-to-trial relationships.
    if not set(patients["trial_id"]).issubset(
        set(trials["trial_id"])
    ):
        raise ValueError(
            "Patient records contain unknown trial IDs."
        )

    # Validate visit-to-patient relationships.
    if not set(visits["patient_id"]).issubset(
        set(patients["patient_id"])
    ):
        raise ValueError(
            "Visit records contain unknown patient IDs."
        )

    # Validate laboratory records.
    if not set(labs["visit_id"]).issubset(
        set(visits["visit_id"])
    ):
        raise ValueError(
            "Lab records contain unknown visit IDs."
        )

    if labs[
        [
            "lab_result_id",
            "patient_id",
            "trial_id",
            "visit_id",
            "collection_date",
        ]
    ].isna().any().any():
        raise ValueError(
            "Lab identifiers, relationships, and collection dates "
            "cannot be null."
        )

    if labs["result_value"].isna().any():
        raise ValueError(
            "Lab result values cannot be null."
        )

    if labs["lab_result_id"].duplicated().any():
        raise ValueError(
            "Lab result identifiers must be unique after deduplication."
        )

    # Validate patient and visit trial consistency.
    patient_trials = patients.set_index(
        "patient_id"
    )["trial_id"]

    visit_lookup = visits.set_index(
        "visit_id"
    )[["patient_id", "trial_id"]]

    if not visits.apply(
        lambda row: (
            patient_trials.get(row["patient_id"]) == row["trial_id"]
        ),
        axis=1,
    ).all():
        raise ValueError(
            "Visit trial_id must match the participant's trial_id."
        )

    # Validate lab-to-visit consistency.
    for row in labs.itertuples(index=False):
        visit = visit_lookup.loc[row.visit_id]

        if (
            row.patient_id != visit.patient_id
            or row.trial_id != visit.trial_id
        ):
            raise ValueError(
                "Lab participant and trial must match the linked visit."
            )

    # Write validated Silver datasets.
    output = {
        "patients": patients,
        "trials": trials,
        "visits": visits,
        "lab_results": labs,
    }

    silver_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, frame in output.items():
        frame.to_parquet(
            silver_dir / f"{name}.parquet",
            index=False,
        )

    return {
        name: len(frame)
        for name, frame in output.items()
    }
