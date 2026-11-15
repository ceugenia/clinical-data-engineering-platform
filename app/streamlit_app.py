from pathlib import Path

import duckdb
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "warehouse" / "clinical.duckdb"
st.set_page_config(page_title="Clinical Trial Operations", page_icon="🧬", layout="wide")
st.title("Clinical Trial Operations")
st.caption("Synthetic data engineering portfolio project · No real patient data")
if not DB.exists():
    st.warning("Warehouse not found. Run `python -m clinical_pipeline run` from the project root.")
    st.stop()
con = duckdb.connect(str(DB), read_only=True)
try:
    mart = con.execute("select * from mart_trial_operations order by trial_id").df()
    visits = con.execute("select * from fct_visit").df()
    labs = con.execute("select * from stg_lab_results").df()
finally:
    con.close()
a, b, c, d = st.columns(4)
a.metric("Trials", f"{len(mart):,}")
b.metric("Participants", f"{int(mart.participant_count.sum()):,}")
c.metric("Visits", f"{int(mart.total_visits.sum()):,}")
d.metric("Visit completion", f"{100 * visits.completed_flag.mean():.1f}%")
st.subheader("Trial operations overview")
st.dataframe(mart[["trial_id", "trial_name", "therapeutic_area", "phase",
    "participant_count", "enrolled_count", "visit_completion_pct", "out_of_range_pct"]],
    use_container_width=True, hide_index=True)
left, right = st.columns(2)
with left:
    st.subheader("Participants by trial")
    st.bar_chart(mart.set_index("trial_name")[["participant_count"]])
with right:
    st.subheader("Visit completion by trial (%)")
    st.bar_chart(mart.set_index("trial_name")[["visit_completion_pct"]])
st.subheader("Laboratory results")
summary = labs.groupby("analyte", as_index=False).agg(
    measurements=("lab_result_id", "count"), out_of_range=("is_out_of_range", "sum"))
summary["out_of_range_pct"] = (100 * summary.out_of_range / summary.measurements).round(1)
st.dataframe(summary, use_container_width=True, hide_index=True)
st.bar_chart(summary.set_index("analyte")[["out_of_range_pct"]])
