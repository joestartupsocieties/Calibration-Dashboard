from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from sez_calibration.export_outputs import run_pipeline  # noqa: E402
from sez_calibration.explanations import split_reason_codes  # noqa: E402
from sez_calibration.recommendation_engine import load_reason_codes  # noqa: E402


st.set_page_config(
    page_title="SEZ Zone Triage and Calibration Support MVP",
    layout="wide",
)


def scenario_from_sidebar() -> dict[str, object]:
    st.sidebar.subheader("Scenario Controls")
    threshold = st.sidebar.slider("Data confidence threshold", 0.0, 1.0, 0.40, 0.05)
    require_legal_low = st.sidebar.checkbox("Require legal low risk for pilot", value=False)
    require_fiscal = st.sidebar.checkbox("Require fiscal data for pilot", value=False)
    include_construction = st.sidebar.checkbox("Include construction-stage transition candidates", value=True)
    return {
        "data_confidence_threshold": threshold,
        "require_legal_low_risk_for_pilot": require_legal_low,
        "require_fiscal_data_for_pilot": require_fiscal,
        "include_construction_stage_transition_candidates": include_construction,
    }


@st.cache_data(show_spinner=False)
def load_demo_outputs(scenario: tuple[tuple[str, object], ...]) -> dict[str, object]:
    return run_pipeline(ROOT, scenario=dict(scenario), write_outputs=True)


def rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


scenario = scenario_from_sidebar()
result = load_demo_outputs(tuple(sorted(scenario.items())))
frames: dict[str, pd.DataFrame] = result["frames"]
summary: dict[str, object] = result["summary"]
reason_codes = load_reason_codes(ROOT / "config" / "reason_codes_v0_5_lite.yaml")

pages = [
    "Home",
    "Zone Explorer",
    "Data Quality",
    "Legal / Fiscal Placeholder Gates",
    "Recommendation Engine",
    "Scenario Controls - MVP placeholder",
    "Export",
]
page = st.sidebar.radio("Page", pages)

st.title("SEZ Zone Triage and Calibration Support MVP")
st.caption("v0.5-lite - demo only")

if page == "Home":
    st.warning(
        "Demo only. No final legal, fiscal, or incentive decisions. No final tax rates. "
        "Any support-related output is subject to D4 legal review and D5 fiscal verification. "
        "Any cost-based support is temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035."
    )
    st.write(
        "The current normalized data is the 35-zone demo dataset, not the final reconciled 44/54-zone universe. "
        "Exact row-level verification should use the original workbook."
    )
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Zones loaded", summary["zone_records_loaded"])
    c2.metric("Data-quality issues", summary["data_quality_issue_count"])
    c3.metric("Contradictions", summary["contradiction_count"])
    c4.metric("Support screen candidates", summary["possible_pilot_screen_candidates"])
    c5.metric("More data required", summary["more_data_required"])
    st.dataframe(frames["recommendations"], width="stretch", hide_index=True)

elif page == "Zone Explorer":
    zones = frames["zones"].merge(frames["activity"], on=["zone_id", "zone_name"], how="left").merge(
        frames["confidence"], on=["zone_id", "zone_name"], how="left"
    )
    provinces = sorted([p for p in zones["province"].dropna().unique() if str(p).strip()])
    activities = sorted(zones["activity_category"].dropna().unique())
    bands = sorted(zones["data_confidence_band"].dropna().unique())
    c1, c2, c3 = st.columns(3)
    province_filter = c1.multiselect("Province", provinces, default=provinces)
    activity_filter = c2.multiselect("Activity category", activities, default=activities)
    band_filter = c3.multiselect("Data confidence", bands, default=bands)
    filtered = zones[
        zones["province"].isin(province_filter)
        & zones["activity_category"].isin(activity_filter)
        & zones["data_confidence_band"].isin(band_filter)
    ]
    st.dataframe(filtered, width="stretch", hide_index=True)
    selected = st.selectbox("Selected zone", filtered["zone_name"].tolist() if not filtered.empty else [])
    if selected:
        st.json(filtered[filtered["zone_name"] == selected].iloc[0].dropna().to_dict())

elif page == "Data Quality":
    st.subheader("Issue Log")
    severity_values = ["critical", "high", "medium", "low"]
    selected_severity = st.multiselect("Severity", severity_values, default=["critical", "high"])
    issues = frames["issues"]
    st.dataframe(issues[issues["severity"].isin(selected_severity)], width="stretch", hide_index=True)
    st.subheader("Contradiction and Source-Scope Log")
    st.dataframe(frames["contradictions"], width="stretch", hide_index=True)
    st.subheader("Field Completeness")
    st.dataframe(frames["field_completeness"], width="stretch", hide_index=True)
    st.subheader("Confidence Score Distribution")
    st.bar_chart(frames["confidence"]["data_confidence_band"].value_counts())

elif page == "Legal / Fiscal Placeholder Gates":
    st.info("Legal/fiscal values are placeholders pending D4 legal review and D5 fiscal verification. Edits here are demo overrides only.")
    uploaded = st.file_uploader("Upload replacement legal_fiscal_placeholders.csv", type=["csv"])
    if uploaded is not None:
        placeholders = pd.read_csv(uploaded)
    else:
        placeholders = frames["legal"].merge(frames["fiscal"], on=["zone_id", "zone_name"], how="left")
        if "notes" not in placeholders.columns:
            placeholders["notes"] = "Legal/fiscal placeholders pending D4 legal review and D5 fiscal verification."
    edited = st.data_editor(
        placeholders,
        width="stretch",
        hide_index=True,
        column_config={
            "legal_risk_level": st.column_config.SelectboxColumn(options=["low", "medium", "high", "unknown"]),
            "developer_compliance_status": st.column_config.SelectboxColumn(options=["compliant", "partial", "non_compliant", "unknown"]),
            "legal_review_required": st.column_config.CheckboxColumn(),
            "fiscal_exposure_level": st.column_config.SelectboxColumn(options=["low", "medium", "high", "unknown"]),
            "fiscal_data_status": st.column_config.SelectboxColumn(options=["verified", "partial", "missing"]),
        },
    )
    if st.button("Apply demo placeholder overrides"):
        edited.to_csv(ROOT / "data" / "legal_fiscal_placeholders.csv", index=False, encoding="utf-8")
        st.cache_data.clear()
        rerun()

elif page == "Recommendation Engine":
    recs = frames["recommendations"]
    st.dataframe(recs, width="stretch", hide_index=True)
    selected = st.selectbox("Selected zone", recs["zone_name"].tolist())
    rec = recs[recs["zone_name"] == selected].iloc[0]
    explanation = frames["explanations"][frames["explanations"]["zone_id"] == rec["zone_id"]].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Confidence", f"{rec['data_confidence_score']:.2f}", rec["data_confidence_band"])
    c2.metric("Activity", rec["activity_category"])
    c3.metric("Support screen", "Yes" if rec["pilot_eligible_flag"] else "No")
    st.write(explanation["plain_english_explanation"])
    st.write("Hard gates:", rec["hard_gates_triggered"])
    st.write("Next actions:", explanation["next_actions"])
    decoded = [{"reason_code": code, "reason_text": reason_codes.get(code, "Unmapped reason code")} for code in split_reason_codes(rec["reason_codes"])]
    st.dataframe(pd.DataFrame(decoded), width="stretch", hide_index=True)

elif page == "Scenario Controls - MVP placeholder":
    st.write("Current scenario settings")
    st.json(scenario)
    st.dataframe(frames["recommendations"], width="stretch", hide_index=True)

elif page == "Export":
    output_dir = ROOT / "outputs"
    export_files = [
        "zone_triage_prototype.csv",
        "recommendation_explanations.csv",
        "audit_flags.csv",
        "data_quality_issue_log.csv",
        "sez_calibration_demo_outputs.xlsx",
    ]
    for name in export_files:
        path = output_dir / name
        if path.exists():
            st.download_button(
                label=f"Download {name}",
                data=path.read_bytes(),
                file_name=name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if name.endswith(".xlsx") else "text/csv",
            )

