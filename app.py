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


UI_CACHE_VERSION = "v0.5-lite-five-page-ui-2026-07-08"

st.set_page_config(
    page_title="SEZ Zone Triage and Calibration Support MVP",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_demo_outputs(cache_version: str) -> dict[str, object]:
    _ = cache_version
    return run_pipeline(ROOT, write_outputs=True)


def filtered_options(series: pd.Series) -> list[str]:
    return sorted([str(value) for value in series.dropna().unique() if str(value).strip()])


def selected_or_all(label: str, options: list[str]) -> list[str]:
    return st.multiselect(label, options, default=options)


def decode_reason_codes(codes: object, reason_codes: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"reason_code": code, "reason_text": reason_codes.get(code, "Unmapped reason code")}
            for code in split_reason_codes(codes)
        ]
    )


def review_count(recommendations: pd.DataFrame) -> int:
    blank = pd.Series([""] * len(recommendations), index=recommendations.index)
    review_text = (
        recommendations.get("required_legal_action", blank).fillna("")
        + " "
        + recommendations.get("required_fbr_action", blank).fillna("")
        + " "
        + recommendations.get("next_actions", blank).fillna("")
    ).str.lower()
    return int(review_text.str.contains("legal|fbr|fiscal|customs|d4|d5", regex=True).sum())


result = load_demo_outputs(UI_CACHE_VERSION)
frames: dict[str, pd.DataFrame] = result["frames"]
summary: dict[str, object] = result["summary"]
reason_codes = load_reason_codes(ROOT / "config" / "reason_codes_v0_5_lite.yaml")
recommendations = frames["recommendations"]

pages = [
    "Home",
    "Zone Explorer",
    "Data Quality",
    "Recommendation Engine",
    "Export",
]
page = st.sidebar.radio("Page", pages)

st.title("SEZ Zone Triage and Calibration Support MVP")
st.caption("v0.5-lite - demo only")

if page == "Home":
    st.warning("Demo only — no final legal, fiscal, or incentive decisions")
    st.info("All SEZ fiscal incentives phase out by 30 June 2035")
    st.info("Cost-based support is temporary transition support only")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zones loaded", summary["zone_records_loaded"])
    c2.metric("Data-quality issues", summary["data_quality_issue_count"])
    c3.metric("Pilot screen candidates", summary["possible_pilot_screen_candidates"])
    c4.metric("Need legal/fiscal review", review_count(recommendations))

    st.dataframe(
        recommendations[
            [
                "zone_id",
                "zone_name",
                "province",
                "data_confidence_band",
                "activity_category",
                "recommended_treatment",
                "hard_gates_triggered",
                "reason_codes",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

elif page == "Zone Explorer":
    explorer = recommendations.merge(
        frames["zones"],
        on=["zone_id", "zone_name", "province", "operational_status"],
        how="left",
        suffixes=("", "_source"),
    )

    c1, c2, c3, c4 = st.columns(4)
    province_filter = c1.multiselect("Province", filtered_options(explorer["province"]), default=filtered_options(explorer["province"]))
    activity_filter = c2.multiselect(
        "Activity category",
        filtered_options(explorer["activity_category"]),
        default=filtered_options(explorer["activity_category"]),
    )
    confidence_filter = c3.multiselect(
        "Confidence band",
        filtered_options(explorer["data_confidence_band"]),
        default=filtered_options(explorer["data_confidence_band"]),
    )
    recommendation_filter = c4.multiselect(
        "Recommendation",
        filtered_options(explorer["recommended_treatment"]),
        default=filtered_options(explorer["recommended_treatment"]),
    )

    filtered = explorer[
        explorer["province"].isin(province_filter)
        & explorer["activity_category"].isin(activity_filter)
        & explorer["data_confidence_band"].isin(confidence_filter)
        & explorer["recommended_treatment"].isin(recommendation_filter)
    ]

    st.dataframe(
        filtered[
            [
                "zone_id",
                "zone_name",
                "province",
                "activity_category",
                "data_confidence_band",
                "recommended_treatment",
                "hard_gates_triggered",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    selected = st.selectbox("Selected zone", filtered["zone_name"].tolist() if not filtered.empty else [])
    if selected:
        detail = filtered[filtered["zone_name"] == selected].iloc[0].dropna()
        st.subheader("Selected-zone Detail")
        st.json(detail.to_dict())

elif page == "Data Quality":
    st.warning("Current demo uses normalized 35-zone data, not final reconciled 44/54-zone universe")

    st.subheader("Issue Log")
    issue_severity = selected_or_all("Issue severity", ["critical", "high", "medium", "low"])
    issues = frames["issues"]
    st.dataframe(issues[issues["severity"].isin(issue_severity)], width="stretch", hide_index=True)

    st.subheader("Contradiction Log")
    st.dataframe(frames["contradictions"], width="stretch", hide_index=True)

    st.subheader("Confidence Scores")
    st.dataframe(frames["confidence"], width="stretch", hide_index=True)

elif page == "Recommendation Engine":
    triage_columns = [
        "zone_id",
        "zone_name",
        "province",
        "data_confidence_score",
        "data_confidence_band",
        "activity_category",
        "recommended_treatment",
        "hard_gates_triggered",
        "reason_codes",
        "human_review_status",
    ]
    st.dataframe(recommendations[triage_columns], width="stretch", hide_index=True)

    selected = st.selectbox("Selected zone", recommendations["zone_name"].tolist())
    rec = recommendations[recommendations["zone_name"] == selected].iloc[0]
    explanation = frames["explanations"][frames["explanations"]["zone_id"] == rec["zone_id"]].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Confidence", f"{rec['data_confidence_score']:.2f}", rec["data_confidence_band"])
    c2.metric("Activity", rec["activity_category"])
    c3.metric("Human review", rec["human_review_status"])

    st.subheader("Explanation")
    st.write(explanation["plain_english_explanation"])

    st.subheader("Hard Gates")
    st.write(rec["hard_gates_triggered"])

    st.subheader("Reason Codes")
    st.dataframe(decode_reason_codes(rec["reason_codes"], reason_codes), width="stretch", hide_index=True)

    st.subheader("Next Required Actions")
    next_actions = rec.get("next_actions", "")
    if not str(next_actions).strip():
        next_actions = explanation.get("next_actions", "")
    st.write(next_actions)

elif page == "Export":
    output_dir = ROOT / "outputs"
    export_files = [
        "zone_triage_prototype.csv",
        "recommendation_explanations.csv",
        "audit_flags.csv",
        "data_quality_issue_log.csv",
        "contradiction_log.csv",
        "data_confidence_scores.csv",
        "activity_classification.csv",
        "field_completeness.csv",
        "summary.json",
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
