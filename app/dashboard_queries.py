from pathlib import Path

import duckdb
import pandas as pd


MODEL_TABLES = (
    "mart_trial_operations",
    "dim_patient",
    "fct_visit",
    "fct_lab_result",
    "mart_lab_analyte",
    "mart_site_performance",
)


def load_dashboard_data(db_path: Path) -> dict[str, pd.DataFrame]:
    """Load the dashboard's dbt models using a read-only DuckDB connection."""
    db_path = Path(db_path)
    if not db_path.is_file():
        raise FileNotFoundError(f"DuckDB warehouse not found: {db_path}")

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        available = {
            row[0]
            for row in connection.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        }
        missing = sorted(set(MODEL_TABLES) - available)
        if missing:
            raise RuntimeError(
                "Missing dbt models: "
                + ", ".join(missing)
                + ". Run `python -m clinical_pipeline run` first."
            )

        return {
            table: connection.execute(f"SELECT * FROM {table}").fetchdf()
            for table in MODEL_TABLES
        }
    finally:
        connection.close()
