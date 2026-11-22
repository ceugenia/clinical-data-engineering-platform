import os
import json
import subprocess
import shutil
from pathlib import Path
from dagster import asset, get_dagster_logger

# Ensure the src directory is in the Python path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from clinical_pipeline.config import DB_PATH, DBT_DIR, SILVER_DIR, ensure_directories
from clinical_pipeline.generate import generate_data
from clinical_pipeline.ingest import ingest_sources
from clinical_pipeline.transform import transform_to_silver
from clinical_pipeline.incremental import apply_incremental_upserts

logger = get_dagster_logger()

@asset(group_name="source", description="Generate deterministic synthetic clinical CSV data")
def synthetic_source_data(context) -> dict:
    logger.info("Generating synthetic source data...")
    ensure_directories()
    generate_data(seed=42)
    return {"status": "generated"}

@asset(
    deps=[synthetic_source_data], 
    group_name="bronze",
    description="Load raw CSVs into immutable, timestamped Parquet batches"
)
def bronze_layer(context) -> dict:
    logger.info("Ingesting to Bronze Parquet layer...")
    counts = ingest_sources()
    return counts

@asset(
    deps=[bronze_layer], 
    group_name="silver",
    description="Standardize, deduplicate, and anonymize PHI data"
)
def silver_layer(context) -> dict:
    logger.info("Transforming and validating Silver layer (includes PHI anonymization)...")
    counts = transform_to_silver()
    return counts

@asset(
    deps=[silver_layer], 
    group_name="warehouse",
    description="Apply incremental timestamp-aware upserts to DuckDB"
)
def warehouse_layer(context) -> dict:
    logger.info("Applying incremental upserts to DuckDB...")
    result = apply_incremental_upserts()
    return result

@asset(
    deps=[warehouse_layer], 
    group_name="warehouse",
    description="Run dbt build to create dimensional marts and execute data quality tests"
)
def dbt_models(context) -> dict:
    logger.info("Running dbt build and tests...")
    env = os.environ.copy()
    env["CLINICAL_DUCKDB_PATH"] = str(DB_PATH)
    
    dbt_executable = shutil.which("dbt")
    if dbt_executable is None:
        raise RuntimeError("dbt executable not found. Install dbt-duckdb in your active virtual environment.")
        
    subprocess.run(
        [
            dbt_executable,
            "build",
            "--project-dir", str(DBT_DIR),
            "--profiles-dir", str(DBT_DIR),
            "--vars", json.dumps({"silver_dir": str(SILVER_DIR).replace("\\", "/")}),
        ],
        check=True,
        cwd=DBT_DIR.parent,
        env=env,
    )
    return {"status": "dbt_passed"}