import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard_queries import load_dashboard_data

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("CLINICAL_DATA_DIR", ROOT / "data")).resolve()
DB_PATH = DATA_DIR / "warehouse" / "clinical.duckdb"
QUALITY_REPORT = DATA_DIR / "quality" / "quality_report.json"
PIPELINE_LOG = DATA_DIR / "warehouse" / "pipeline_runs.jsonl"

st.set_page_config(
    page_title="Clinical Trial Data Platform",
    page_icon="🧬",
    layout="wide",
)
st.title("Clinical Trial Data Platform")
st.caption(
    "Synthetic clinical-trial operations data · Portfolio demonstration · "
    "No real patient information"
)

if not DB_PATH.exists():
    st.warning(
        "Warehouse not found. From the project root, run "
        "`python -m clinical_pipeline run`."
    )
    st.stop()

try:
    data = load_dashboard_data(DB_PATH)
except Exception as exc:
    st.error(str(exc))
    st.stop()

trials = data["mart_trial_operations"].copy()
patients = data["dim_patient"].copy()
visits = data["fct_visit"].copy()
labs = data["fct_lab_result"].copy()
site_performance = data["mart_site_performance"].copy()
dbt_lab_mart = data["mart_lab_analyte"].copy()

st.sidebar.header("Dashboard filters")
areas = ["All"] + sorted(trials["therapeutic_area"].dropna().unique().tolist())
selected_area = st.sidebar.selectbox("Therapeutic area", areas)
if selected_area != "All":
    trials = trials[trials["therapeutic_area"] == selected_area]

trial_options = ["All"] + sorted(trials["trial_id"].dropna().unique().tolist())
selected_trial = st.sidebar.selectbox("Trial", trial_options)
if selected_trial != "All":
    trials = trials[trials["trial_id"] == selected_trial]

trial_ids = set(trials["trial_id"])
patients = patients[patients["trial_id"].isin(trial_ids)]

site_options = ["All"] + sorted(patients["site_id"].dropna().unique().tolist())
selected_site = st.sidebar.selectbox("Site", site_options)
if selected_site != "All":
    patients = patients[patients["site_id"] == selected_site]

patient_ids = set(patients["patient_id"])
visits = visits[visits["patient_id"].isin(patient_ids)]
labs = labs[labs["patient_id"].isin(patient_ids)]
site_performance = site_performance[
    site_performance["trial_id"].isin(trial_ids)
]
if selected_site != "All":
    site_performance = site_performance[
        site_performance["site_id"] == selected_site
    ]

visit_statuses = ["All"] + sorted(visits["visit_status"].dropna().unique().tolist())
selected_visit_status = st.sidebar.selectbox("Visit status", visit_statuses)
if selected_visit_status != "All":
    visits = visits[visits["visit_status"] == selected_visit_status]

analyte_options = ["All"] + sorted(labs["analyte"].dropna().unique().tolist())
selected_analyte = st.sidebar.selectbox("Analyte", analyte_options)
if selected_analyte != "All":
    labs = labs[labs["analyte"] == selected_analyte]

if not labs.empty and "collection_date" in labs.columns:
    labs["collection_date"] = pd.to_datetime(labs["collection_date"])
    min_date = labs["collection_date"].min().date()
    max_date = labs["collection_date"].max().date()
    selected_dates = st.sidebar.date_input(
        "Collection date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
        labs = labs[
            labs["collection_date"].dt.date.between(start_date, end_date)
        ]

participant_count = len(patients)
visit_count = len(visits)
overall_completion = (
    float(visits["completed_flag"].mean() * 100)
    if not visits.empty
    else 0.0
)

a, b, c, d = st.columns(4)
a.metric("Trials", f"{len(trials):,}")
b.metric("Participants", f"{participant_count:,}")
c.metric("Visits (filtered)", f"{visit_count:,}")
d.metric("Visit completion (filtered)", f"{overall_completion:.1f}%")

st.subheader("Trial operations")
display_columns = [
    "trial_id", "trial_name", "therapeutic_area", "phase",
    "participant_count", "enrolled_count", "total_visits",
    "completed_visits", "visit_completion_pct", "out_of_range_pct",
]
st.dataframe(
    trials[[column for column in display_columns if column in trials.columns]],
    use_container_width=True,
    hide_index=True,
)

left, right = st.columns(2)
with left:
    st.subheader("Participants by trial")
    st.bar_chart(trials.set_index("trial_name")[["participant_count"]])
with right:
    st.subheader("Visit completion by trial")
    st.bar_chart(trials.set_index("trial_name")[["visit_completion_pct"]])

st.subheader("Site performance")
if not site_performance.empty:
    st.dataframe(site_performance, use_container_width=True, hide_index=True)
    st.bar_chart(
        site_performance.set_index("site_id")[["visit_completion_pct"]]
    )
else:
    st.info("No site-level records are available for the selected filters.")

st.subheader("Filtered laboratory results")
if not labs.empty:
    filtered_lab_summary = (
        labs.groupby(["analyte", "unit"], as_index=False)
        .agg(
            measurement_count=("lab_result_id", "count"),
            out_of_range_count=("is_out_of_range", "sum"),
            average_result=("result_value", "mean"),
        )
    )
    filtered_lab_summary["out_of_range_pct"] = (
        100
        * filtered_lab_summary["out_of_range_count"]
        / filtered_lab_summary["measurement_count"]
    ).round(1)
    st.dataframe(
        filtered_lab_summary,
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(
        filtered_lab_summary.set_index("analyte")[["out_of_range_pct"]]
    )
else:
    st.info("No laboratory records match the selected filters.")

with st.expander("Published dbt analyte mart"):
    filtered_dbt_lab_mart = dbt_lab_mart[
        dbt_lab_mart["trial_id"].isin(trial_ids)
    ]
    if selected_analyte != "All":
        filtered_dbt_lab_mart = filtered_dbt_lab_mart[
            filtered_dbt_lab_mart["analyte"] == selected_analyte
        ]
    st.dataframe(
        filtered_dbt_lab_mart,
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Data quality")
if QUALITY_REPORT.exists():
    quality = json.loads(QUALITY_REPORT.read_text(encoding="utf-8"))
    q1, q2, q3 = st.columns(3)
    q1.metric("Quality status", quality.get("status", "unknown").upper())
    q2.metric("Silver rows", f"{quality.get('totals', {}).get('silver_rows', 0):,}")
    q3.metric(
        "Deduplicated rows",
        f"{quality.get('totals', {}).get('deduplicated_rows', 0):,}",
    )
    with st.expander("View quality checks and table metrics"):
        st.json(quality)
else:
    st.info("No quality report found. Run the pipeline to generate one.")

st.subheader("Pipeline run history")
if PIPELINE_LOG.exists():
    records = [
        json.loads(line)
        for line in PIPELINE_LOG.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if records:
        history = pd.DataFrame(records).sort_values(
            "started_at", ascending=False
        )
        history_columns = [
            "run_id", "status", "started_at",
            "duration_seconds", "dbt", "failed_stage",
        ]
        st.dataframe(
            history[[column for column in history_columns if column in history]],
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No pipeline audit log found yet.")
