from dagster import Definitions, load_assets_from_dbt_project
from dagster_dbt import DbtCliResource
from .assets import synthetic_source_data, bronze_layer, silver_layer, warehouse_layer, dbt_models

# Point to your existing dbt folder at the project root
DBT_PROJECT_DIR = "dbt"

# Define the dbt CLI resource
dbt_cli_resource = DbtCliResource(project_dir=DBT_PROJECT_DIR)

# Load all dbt models as Dagster assets automatically
dbt_assets = load_assets_from_dbt_project(
    project_dir=DBT_PROJECT_DIR,
    dbt=dbt_cli_resource,
    key_prefix="warehouse"
)

# Combine Python and dbt assets into a single Definitions object
defs = Definitions(
    assets=[
        synthetic_source_data, 
        bronze_layer, 
        silver_layer, 
        warehouse_layer, 
        dbt_models,
        *dbt_assets
    ],
    resources={
        "dbt": dbt_cli_resource,
    }
)