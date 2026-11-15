import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("CLINICAL_DATA_DIR", ROOT / "data")).resolve()
SOURCE_DIR = DATA_DIR / "source"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
QUALITY_DIR = DATA_DIR / "quality"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
DB_PATH = WAREHOUSE_DIR / "clinical.duckdb"
PIPELINE_LOG_PATH = WAREHOUSE_DIR / "pipeline_runs.jsonl"
QUALITY_REPORT_PATH = QUALITY_DIR / "quality_report.json"
DBT_DIR = ROOT / "dbt"
TABLES = ("patients", "trials", "visits", "lab_results")


def ensure_directories() -> None:
    for path in (
        SOURCE_DIR,
        BRONZE_DIR,
        SILVER_DIR,
        QUALITY_DIR,
        WAREHOUSE_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)
