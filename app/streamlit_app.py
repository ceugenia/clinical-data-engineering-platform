
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from dashboard_queries import load_dashboard_data


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("CLINICAL_DATA_DIR", ROOT / "data")).resolve()

DB_PATH = DATA_DIR / "warehouse" / "clinical.duckdb"
QUALITY_REPORT = DATA_DIR / "quality" / "quality_report.json"
PIPELINE_LOG = DATA_DIR / "warehouse" / "pipeline_runs.jsonl"

st.set_page_config(
    page_title="Clinical Data Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# DESIGN SYSTEM
# ---------------------------------------------------------

st.markdown(
    """
    <style>
    @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap'
    );

    :root {
        --navy: #14283F;
        --navy-light: #203B58;
        --teal: #0D9488;
        --teal-light: #CCFBF1;
        --background: #F4F7FB;
        --surface: #FFFFFF;
        --text: #243449;
        --muted: #718096;
        --border: #E5EAF1;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    .stApp {
        background-color: var(--background);
    }

    [data-testid="stHeader"] {
        background-color: transparent;
    }

    [data-testid="stSidebar"] {
        background-color: var(--navy);
        border-right: 1px solid #263F59;
    }

    [data-testid="stSidebar"] * {
        color: #E7EEF7;
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #CBD5E1;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background-color: #203B58;
        border-color: #3B536C;
    }

    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #FFFFFF;
    }

    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .dashboard-header {
        background: linear-gradient(
            120deg,
            #14283F 0%,
            #203F5D 65%,
            #0D9488 120%
        );
        padding: 30px 34px;
        border-radius: 18px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 8px 24px rgba(20, 40, 63, 0.12);
    }

    .dashboard-header h1 {
        color: white;
        font-size: 29px;
        font-weight: 800;
        margin: 0 0 8px 0;
        letter-spacing: -0.8px;
    }

    .dashboard-header p {
        color: #D8E8F2;
        font-size: 14px;
        margin: 0;
    }

    .section-heading {
        color: var(--navy);
        font-size: 19px;
        font-weight: 800;
        margin-top: 12px;
        margin-bottom: 4px;
    }

    .section-description {
        color: var(--muted);
        font-size: 13px;
        margin-bottom: 15px;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 19px 20px;
        box-shadow: 0 3px 12px rgba(25, 45, 70, 0.035);
    }

    [data-testid="stMetricLabel"] {
        color: var(--muted);
        font-size: 13px;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        color: var(--navy);
        font-size: 28px;
        font-weight: 800;
    }

    [data-testid="stMetricDelta"] {
        font-size: 12px;
    }

    [data-testid="stTabs"] button {
        font-weight: 700;
        color: var(--muted);
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--teal);
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: white;
        border-color: var(--border);
        border-radius: 14px;
    }

    .status-label {
        color: var(--teal);
        background: var(--teal-light);
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 800;
        display: inline-block;
    }

    .footer {
        text-align: center;
        color: #94A3B8;
        font-size: 12px;
        padding-top: 30px;
        padding-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def section_heading(title, description=None):
    st.markdown(
        f'<div class="section-heading">{title}</div>',
        unsafe_allow_html=True,
    )

    if description:
        st.markdown(
            f'<div class="section-description">{description}</div>',
            unsafe_allow_html=True,
        )


def safe_options(dataframe, column):
    if column not in dataframe.columns:
        return []

    return sorted(
        dataframe[column].dropna().astype(str).unique().tolist()
    )


def read_quality_report():
    if not QUALITY_REPORT.exists():
        return {}

    try:
        return json.loads(
            QUALITY_REPORT.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        return {}


def read_pipeline_history():
    if not PIPELINE_LOG.exists():
        return pd.DataFrame()

    records = []

    try:
        for line in PIPELINE_LOG.read_text(
            encoding="utf-8"
        ).splitlines():
            if line.strip():
                records.append(json.loads(line))
    except (json.JSONDecodeError, OSError):
        return pd.DataFrame()

    if not records:
        return pd.DataFrame()

    history = pd.DataFrame(records)

    if "started_at" in history.columns:
        history = history.sort_values(
            "started_at",
            ascending=False,
        )

    return history


def show_table(dataframe, columns=None):
    if dataframe.empty:
        st.info("No records are available for the selected filters.")
        return

    if columns:
        available = [
            column for column in columns
            if column in dataframe.columns
        ]
        dataframe = dataframe[available]

    st.dataframe(
        dataframe,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    """
    <div class="dashboard-header">
        <h1>Clinical Data Intelligence</h1>
        <p>
            Clinical trial operations, laboratory analytics,
            data quality, and pipeline monitoring.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# WAREHOUSE CONNECTION
# ---------------------------------------------------------

if not DB_PATH.exists():
    st.warning(
        "The DuckDB warehouse was not found. "
        "Run `python -m clinical_pipeline run` "
        "from your project root."
    )
    st.stop()

try:
    data = load_dashboard_data(DB_PATH)
except Exception as exc:
    st.error(f"Unable to load dashboard data: {exc}")
    st.stop()


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

trials = data["mart_trial_operations"].copy()
patients = data["dim_patient"].copy()
visits = data["fct_visit"].copy()
labs = data["fct_lab_result"].copy()
site_performance = data["mart_site_performance"].copy()
dbt_lab_mart = data["mart_lab_analyte"].copy()

quality = read_quality_report()
history = read_pipeline_history()


# ---------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------

st.sidebar.markdown("## CLINICAL DATA")
st.sidebar.caption("INTELLIGENCE PLATFORM")
st.sidebar.divider()

st.sidebar.markdown("### Dashboard filters")

if st.sidebar.button("Refresh dashboard", use_container_width=True):
    st.rerun()

areas = ["All"] + safe_options(trials, "therapeutic_area")

selected_area = st.sidebar.selectbox(
    "Therapeutic area",
    areas,
)

if selected_area != "All":
    trials = trials[
        trials["therapeutic_area"].astype(str) == selected_area
    ]

trial_options = ["All"] + safe_options(trials, "trial_id")

selected_trial = st.sidebar.selectbox(
    "Clinical trial",
    trial_options,
)

if selected_trial != "All":
    trials = trials[
        trials["trial_id"].astype(str) == selected_trial
    ]

trial_ids = set(trials["trial_id"].dropna())

patients = patients[
    patients["trial_id"].isin(trial_ids)
]

site_options = ["All"] + safe_options(patients, "site_id")

selected_site = st.sidebar.selectbox(
    "Research site",
    site_options,
)

if selected_site != "All":
    patients = patients[
        patients["site_id"].astype(str) == selected_site
    ]

patient_ids = set(patients["patient_id"].dropna())

visits = visits[
    visits["patient_id"].isin(patient_ids)
].copy()

labs = labs[
    labs["patient_id"].isin(patient_ids)
].copy()

site_performance = site_performance[
    site_performance["trial_id"].isin(trial_ids)
].copy()

if selected_site != "All":
    site_performance = site_performance[
        site_performance["site_id"].astype(str) == selected_site
    ]

# Preserve the unfiltered visit set for the completion KPI.
visits_for_completion = visits.copy()

visit_statuses = ["All"] + safe_options(visits, "visit_status")

selected_visit_status = st.sidebar.selectbox(
    "Visit status",
    visit_statuses,
)

if selected_visit_status != "All":
    visits = visits[
        visits["visit_status"].astype(str) == selected_visit_status
    ]

analyte_options = ["All"] + safe_options(labs, "analyte")

selected_analyte = st.sidebar.selectbox(
    "Laboratory analyte",
    analyte_options,
)

if selected_analyte != "All":
    labs = labs[
        labs["analyte"].astype(str) == selected_analyte
    ]

# Collection date filter
if not labs.empty and "collection_date" in labs.columns:
    labs["collection_date"] = pd.to_datetime(
        labs["collection_date"],
        errors="coerce",
    )

    valid_dates = labs["collection_date"].dropna()

    if not valid_dates.empty:
        min_date = valid_dates.min().date()
        max_date = valid_dates.max().date()

        selected_dates = st.sidebar.date_input(
            "Collection date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates

            labs = labs[
                labs["collection_date"].dt.date.between(
                    start_date,
                    end_date,
                )
            ]

st.sidebar.divider()
st.sidebar.caption(
    "Demonstration environment · Synthetic data only"
)


# ---------------------------------------------------------
# CALCULATE KPIs
# ---------------------------------------------------------

participant_count = len(patients)
trial_count = len(trials)
visit_count = len(visits)
lab_count = len(labs)
site_count = (
    patients["site_id"].nunique()
    if "site_id" in patients.columns
    else 0
)

overall_completion = (
    float(visits_for_completion["completed_flag"].mean() * 100)
    if not visits_for_completion.empty
    and "completed_flag" in visits_for_completion.columns
    else 0.0
)

out_of_range_pct = (
    float(labs["is_out_of_range"].mean() * 100)
    if not labs.empty and "is_out_of_range" in labs.columns
    else 0.0
)


# ---------------------------------------------------------
# NAVIGATION TABS
# ---------------------------------------------------------

overview_tab, operations_tab, laboratory_tab, quality_tab = st.tabs(
    [
        "Overview",
        "Trial Operations",
        "Laboratory Intelligence",
        "Data Operations",
    ]
)


# ---------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------

with overview_tab:
    section_heading(
        "Platform overview",
        "A consolidated view of clinical trial activity and performance.",
    )

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("Clinical trials", f"{trial_count:,}")
    k2.metric("Participants", f"{participant_count:,}")
    k3.metric("Research sites", f"{site_count:,}")
    k4.metric("Visits", f"{visit_count:,}")
    k5.metric("Lab measurements", f"{lab_count:,}")

    st.write("")

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            section_heading(
                "Participant enrollment",
                "Participant distribution across clinical trials.",
            )

            if (
                not trials.empty
                and "trial_name" in trials.columns
                and "participant_count" in trials.columns
            ):
                chart = trials.set_index("trial_name")[
                    ["participant_count"]
                ]
                st.bar_chart(chart, color="#0D9488")
            else:
                st.info("Enrollment data is unavailable.")

    with right:
        with st.container(border=True):
            section_heading(
                "Visit completion",
                "Percentage of visits completed across trials.",
            )

            if (
                not trials.empty
                and "trial_name" in trials.columns
                and "visit_completion_pct" in trials.columns
            ):
                chart = trials.set_index("trial_name")[
                    ["visit_completion_pct"]
                ]
                st.bar_chart(chart, color="#315B85")
            else:
                st.info("Visit completion data is unavailable.")

    st.write("")

    with st.container(border=True):
        section_heading(
            "Clinical trial portfolio",
            "Current operational metrics for the selected trials.",
        )

        show_table(
            trials,
            [
                "trial_id",
                "trial_name",
                "therapeutic_area",
                "phase",
                "participant_count",
                "enrolled_count",
                "total_visits",
                "completed_visits",
                "visit_completion_pct",
                "out_of_range_pct",
            ],
        )


# ---------------------------------------------------------
# TRIAL OPERATIONS
# ---------------------------------------------------------

with operations_tab:
    section_heading(
        "Trial operations",
        "Monitor participant enrollment, visit activity, and site performance.",
    )

    a, b, c = st.columns(3)

    a.metric("Participants", f"{participant_count:,}")
    b.metric("Visit completion", f"{overall_completion:.1f}%")
    c.metric("Filtered visits", f"{visit_count:,}")

    st.write("")

    with st.container(border=True):
        section_heading(
            "Site performance",
            "Compare operational performance across research sites.",
        )

        if not site_performance.empty:
            show_table(site_performance)

            if (
                "site_id" in site_performance.columns
                and "visit_completion_pct" in site_performance.columns
            ):
                chart = site_performance.set_index("site_id")[
                    ["visit_completion_pct"]
                ]
                st.bar_chart(chart, color="#0D9488")
        else:
            st.info("No site-level records match the selected filters.")

    st.write("")

    with st.container(border=True):
        section_heading(
            "Visit activity",
            "Visit records after applying your selected filters.",
        )

        show_table(
            visits,
            [
                "visit_id",
                "patient_id",
                "trial_id",
                "visit_number",
                "visit_type",
                "visit_date",
                "visit_status",
                "completed_flag",
            ],
        )


# ---------------------------------------------------------
# LABORATORY INTELLIGENCE
# ---------------------------------------------------------

with laboratory_tab:
    section_heading(
        "Laboratory intelligence",
        "Analyze laboratory measurements and reference-range indicators.",
    )

    a, b, c = st.columns(3)

    a.metric("Measurements", f"{lab_count:,}")
    b.metric("Out-of-range results", f"{out_of_range_pct:.1f}%")
    c.metric(
        "Analytes",
        f"{labs['analyte'].nunique():,}"
        if not labs.empty and "analyte" in labs.columns
        else "0",
    )

    st.write("")

    if not labs.empty:
        if (
            "analyte" in labs.columns
            and "unit" in labs.columns
            and "lab_result_id" in labs.columns
        ):
            filtered_lab_summary = (
                labs.groupby(
                    ["analyte", "unit"],
                    as_index=False,
                )
                .agg(
                    measurement_count=("lab_result_id", "count"),
                    average_result=("result_value", "mean"),
                    out_of_range_count=("is_out_of_range", "sum"),
                )
            )

            filtered_lab_summary["out_of_range_pct"] = (
                100
                * filtered_lab_summary["out_of_range_count"]
                / filtered_lab_summary["measurement_count"]
            ).round(1)

            with st.container(border=True):
                section_heading(
                    "Reference-range indicators",
                    "Percentage of measurements flagged outside reference ranges.",
                )

                st.bar_chart(
                    filtered_lab_summary.set_index("analyte")[
                        ["out_of_range_pct"]
                    ],
                    color="#D97757",
                )

            st.write("")

            with st.container(border=True):
                section_heading(
                    "Analyte summary",
                    "Aggregated laboratory measurements.",
                )

                show_table(filtered_lab_summary)

        with st.container(border=True):
            section_heading(
                "Laboratory records",
                "Individual measurements matching your selected filters.",
            )

            show_table(
                labs,
                [
                    "lab_result_id",
                    "patient_id",
                    "trial_id",
                    "visit_id",
                    "collection_date",
                    "analyte",
                    "result_value",
                    "unit",
                    "reference_low",
                    "reference_high",
                    "is_out_of_range",
                ],
            )

    else:
        st.info("No laboratory records match the selected filters.")

    with st.expander("Published dbt analyte mart"):
        filtered_dbt_lab_mart = dbt_lab_mart[
            dbt_lab_mart["trial_id"].isin(trial_ids)
        ]

        if selected_analyte != "All":
            filtered_dbt_lab_mart = filtered_dbt_lab_mart[
                filtered_dbt_lab_mart["analyte"].astype(str)
                == selected_analyte
            ]

        show_table(filtered_dbt_lab_mart)


# ---------------------------------------------------------
# DATA OPERATIONS
# ---------------------------------------------------------

with quality_tab:
    section_heading(
        "Data operations",
        "Monitor data quality, warehouse metrics, and pipeline execution.",
    )

    if quality:
        totals = quality.get("totals", {})

        status = str(
            quality.get("status", "unknown")
        ).upper()

        q1, q2, q3 = st.columns(3)

        q1.metric("Quality status", status)
        q2.metric(
            "Silver rows",
            f"{totals.get('silver_rows', 0):,}",
        )
        q3.metric(
            "Deduplicated rows",
            f"{totals.get('deduplicated_rows', 0):,}",
        )

        st.write("")

        with st.container(border=True):
            section_heading(
                "Quality report",
                "Detailed output from the pipeline quality checks.",
            )

            checks = quality.get("checks", [])

            if isinstance(checks, list) and checks:
                st.dataframe(
                    pd.DataFrame(checks),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.json(quality)

            with st.expander("View complete quality report"):
                st.json(quality)

    else:
        st.info(
            "No quality report found. Run the pipeline to generate one."
        )

    st.write("")

    with st.container(border=True):
        section_heading(
            "Pipeline execution history",
            "Recent pipeline runs and their execution status.",
        )

        if not history.empty:
            history_columns = [
                "run_id",
                "status",
                "started_at",
                "duration_seconds",
                "dbt",
                "failed_stage",
            ]

            show_table(history, history_columns)

            if "status" in history.columns:
                status_counts = (
                    history["status"]
                    .fillna("unknown")
                    .astype(str)
                    .value_counts()
                )

                st.caption("Pipeline run status distribution")
                st.bar_chart(status_counts)

        else:
            st.info("No pipeline audit history is available yet.")


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        Clinical Data Intelligence Platform
        &nbsp;|&nbsp; Built with Python, DuckDB, dbt, and Streamlit
        <br>
        Portfolio demonstration using synthetic clinical data.
        No real patient information.
    </div>
    """,
    unsafe_allow_html=True,
)
