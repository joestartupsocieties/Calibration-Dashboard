from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from sez_calibration.export_outputs import run_pipeline  # noqa: E402
from sez_calibration.explanations import split_reason_codes  # noqa: E402
from sez_calibration.recommendation_engine import load_reason_codes  # noqa: E402


APP_TITLE = "SEZ Fiscal-Calibrated Triage & Incentive Screening Prototype"
APP_SUBTITLE = (
    "Decision-support prototype for SEZ fiscal exposure, legal/compliance triage, "
    "calibration logic, and pilot screening."
)
WARNING_TEXT = (
    "Prototype / logic test only. Outputs are provisional screening results for human review. "
    "This tool does not approve incentives, set tax rates, calculate final fiscal cost, or replace "
    "BOI, FBR, Finance, SEZA, legal, IMF, or programme review."
)
FOOTER_TEXT = (
    "This prototype supports structured analysis and discussion. It does not make binding legal, "
    "fiscal, tax, incentive, or policy decisions. Final determinations require validated source data "
    "and approval by relevant government, legal, fiscal, and programme authorities."
)
UI_CACHE_VERSION = "v0.5-lite-decision-support-prototype-2026-07-08"

PAGES = [
    "Executive View",
    "Zone Explorer",
    "Recommendation Engine",
    "Data Intake",
    "Data Validation & Source Confidence",
    "KPI Assurance",
    "Advanced Model Settings",
    "Export",
]
CONFIDENCE_BANDS = ["medium", "high"]
DATA_INTAKE_TYPES = [
    "Zone master / profile data",
    "Enterprise / plot-level data",
    "Legal / contractual documents",
    "FBR / tax data",
    "Customs / import-exemption data",
    "Infrastructure / utilities data",
    "KPI performance data",
    "Verification / proxy data",
    "Stakeholder consultation data",
]
REQUIRED_FIELDS_BY_INTAKE_TYPE = {
    "Zone master / profile data": [
        "zone_id",
        "zone_name",
        "province",
        "developer_name",
        "developer_mode",
        "zone_type",
        "operational_status",
        "total_area_acres",
        "industrial_area_acres",
        "source_file",
        "source_row",
    ],
    "Enterprise / plot-level data": [
        "zone_id",
        "enterprise_id",
        "enterprise_name",
        "plot_id",
        "plot_area_acres",
        "production_status",
        "production_start_date",
        "employment",
        "exports",
        "investment",
        "source_file",
    ],
    "Legal / contractual documents": [
        "zone_id",
        "development_agreement_status",
        "enterprise_certificate_status",
        "sunset_clause",
        "change_in_law_clause",
        "arbitration_clause",
        "compensation_clause",
        "legal_review_owner",
        "source_file",
    ],
    "FBR / tax data": [
        "zone_id",
        "cit_foregone",
        "customs_exemptions",
        "tax_paid",
        "incentive_utilization",
        "tax_year",
        "fbr_source_reference",
    ],
    "Customs / import-exemption data": [
        "zone_id",
        "import_exemption_value",
        "customs_duty_foregone",
        "exemption_type",
        "goods_category",
        "tax_year",
        "source_file",
    ],
    "Infrastructure / utilities data": [
        "zone_id",
        "electricity_status",
        "gas_status",
        "water_status",
        "access_roads_status",
        "internal_roads_status",
        "wastewater_status",
        "one_window_facilitation_status",
        "source_file",
    ],
    "KPI performance data": [
        "zone_id",
        "employment",
        "exports",
        "investment",
        "production_value",
        "operating_enterprises",
        "kpi_period",
        "source_file",
    ],
    "Verification / proxy data": [
        "zone_id",
        "satellite_or_site_visit_date",
        "production_proxy",
        "utility_consumption_proxy",
        "verification_method",
        "verifier",
        "source_file",
    ],
    "Stakeholder consultation data": [
        "zone_id",
        "stakeholder_group",
        "consultation_date",
        "issue_raised",
        "validation_outcome",
        "source_file",
    ],
}
SEVERITY_LABELS = {
    "critical": "Blocking",
    "high": "Material",
    "medium": "Caution",
    "low": "Info",
    "warning": "Caution",
    "info": "Info",
}
POSTURE_DEFAULTS = {
    "Screening Mode": {
        "require_legal_low_risk_for_pilot": False,
        "require_fiscal_data_for_pilot": False,
        "include_construction_stage_transition_candidates": True,
        "minimum_data_confidence_band_for_pilot": "medium",
        "treat_unknown_developer_compliance_as_blocker": False,
    },
    "Conservative IMF Mode": {
        "require_legal_low_risk_for_pilot": True,
        "require_fiscal_data_for_pilot": True,
        "include_construction_stage_transition_candidates": False,
        "minimum_data_confidence_band_for_pilot": "high",
        "treat_unknown_developer_compliance_as_blocker": True,
    },
    "Exploratory Pilot Mode": {
        "require_legal_low_risk_for_pilot": False,
        "require_fiscal_data_for_pilot": False,
        "include_construction_stage_transition_candidates": True,
        "minimum_data_confidence_band_for_pilot": "medium",
        "treat_unknown_developer_compliance_as_blocker": False,
    },
}

FIELD_LABELS = {
    "zone_id": "Zone ID",
    "zone_name": "Zone",
    "province": "Province",
    "developer_name": "Developer",
    "developer_mode": "Developer Mode",
    "zone_type": "Zone Type",
    "operational_status": "Reported Status",
    "total_area_acres": "Total Area (acres)",
    "industrial_area_acres": "Industrial Area (acres)",
    "allotted_area_acres": "Allotted Area (acres)",
    "vacant_area_acres": "Vacant Area (acres)",
    "under_construction_area_acres": "Under Construction Area (acres)",
    "under_production_area_acres": "Under Production Area (acres)",
    "unsold_area_acres": "Unsold Area (acres)",
    "number_allottees": "Allottees",
    "electricity_status": "Electricity",
    "gas_status": "Gas",
    "water_status": "Water",
    "wastewater_status": "Wastewater",
    "roads_status": "Roads",
    "source_file": "Source Package",
    "source_row": "Source Row",
    "data_confidence_score": "Confidence Score",
    "data_confidence_band": "Data Confidence",
    "activity_category": "Reported Activity",
    "recommended_treatment": "Provisional Treatment",
    "hard_gates_display": "Hard Gates",
    "reason_codes": "Main Reason Codes",
    "legal_risk_level": "Legal Status",
    "fiscal_exposure_level": "Fiscal Status",
    "developer_compliance_status": "Developer Compliance",
    "required_data_action": "Data Action",
    "required_legal_action": "Legal Action",
    "required_fbr_action": "Fiscal/FBR Action",
    "human_review_status": "Human Review",
    "enterprise_compliance_status": "Enterprise Compliance",
    "fiscal_data_status": "Fiscal Data Status",
    "additionality_confidence": "Additionality Confidence",
    "incentive_effectiveness_confidence": "Incentive-Effectiveness Confidence",
    "net_fiscal_economic_impact": "Net Fiscal/Economic Impact",
    "fiscal_exposure_status": "Fiscal Exposure Status",
    "legal_status": "Legal Status",
    "compliance_status": "Compliance Status",
    "provisional_treatment": "Provisional Treatment",
    "illustrative_support_treatment": "Illustrative Support Treatment",
    "illustrative_instrument_options": "Illustrative Instrument Options",
    "why": "Why",
    "blocking_validation_requirements": "Blocking Validation Requirements",
    "data_gaps": "Data Gaps",
    "validator_owner": "Validator / Owner",
    "issue_id": "Flag ID",
    "dataset_name": "Dataset",
    "field_name": "Field",
    "issue_type": "Flag Type",
    "severity": "Severity",
    "issue_description": "Description",
    "recommended_fix": "Suggested Resolution",
    "model_impact": "Model Impact",
    "resolved_flag": "Resolved",
    "date_logged": "Date Logged",
    "confidence_reason": "Confidence Rationale",
    "field_name": "Field",
    "present_count": "Present Records",
    "missing_count": "Missing Records",
    "completeness_pct": "Completeness",
    "criticality": "Criticality",
    "recommended_action": "Suggested Action",
}

GATE_LABELS = {
    "low_data_confidence": "Data confidence is too low for fiscal or calibration use",
    "high_legal_risk": "High legal or contractual risk; D4 legal review required",
    "legal_review_required": "Legal classification is unknown or placeholder-based; D4 legal review required",
    "compliance_non_compliant": "Developer or enterprise compliance concern; sanction / withdrawal review required",
    "compliance_validation_required": "Developer or enterprise compliance requires validation",
    "fiscal_exposure_missing": "Fiscal exposure missing or placeholder-based; D5/FBR/customs verification required",
    "high_fiscal_exposure": "High fiscal exposure requires D5/FBR validation",
    "additionality_uncertain": "Additionality is uncertain; activity is not proof incentives caused the activity",
    "weak_incentive_effectiveness_evidence": "Vacancy or allotment-only movement is weak evidence of incentive effectiveness",
    "scenario_minimum_confidence_band": "Advanced Model Settings: minimum confidence band not met",
    "scenario_legal_low_risk_required": "Advanced Model Settings: low legal risk required",
    "scenario_fiscal_data_required": "Advanced Model Settings: D5 fiscal data required",
    "scenario_construction_excluded": "Advanced Model Settings: construction-stage zones excluded",
    "scenario_unknown_developer_compliance_blocker": "Advanced Model Settings: developer compliance must be known",
}


st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {display: none;}
        .block-container {padding-top: 1.2rem; padding-bottom: 2.2rem; max-width: 1400px;}
        h1 {letter-spacing: 0;}
        .prototype-kicker {
            color: #4b5563;
            font-size: 0.95rem;
            margin-bottom: 0.3rem;
        }
        .answer-box, .mapping-card, .metric-card, .note-card, .output-card {
            border: 1px solid #d8dee9;
            border-radius: 8px;
            background: #ffffff;
            padding: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .metric-card {
            min-height: 112px;
            border-left: 4px solid #2563eb;
        }
        .metric-label {
            color: #4b5563;
            font-size: 0.78rem;
            line-height: 1.2;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .metric-value {
            color: #111827;
            font-size: 2rem;
            font-weight: 650;
            line-height: 1.15;
            margin-top: 0.35rem;
        }
        .metric-note {
            color: #6b7280;
            font-size: 0.82rem;
            margin-top: 0.25rem;
        }
        .badge-row {display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.35rem 0 1rem 0;}
        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.22rem 0.58rem;
            font-size: 0.78rem;
            font-weight: 600;
            background: #eef2ff;
            color: #3730a3;
        }
        .badge.warning {background: #fff7ed; color: #9a3412;}
        .badge.good {background: #ecfdf5; color: #047857;}
        .badge.neutral {background: #f3f4f6; color: #374151;}
        .section-rule {
            height: 1px;
            background: #e5e7eb;
            margin: 1.2rem 0 1rem 0;
        }
        .footer-disclaimer {
            border-top: 1px solid #e5e7eb;
            color: #4b5563;
            font-size: 0.84rem;
            margin-top: 2rem;
            padding-top: 0.9rem;
        }
        .output-card {
            border-left: 5px solid #0f766e;
            background: #f8fafc;
            margin: 0.5rem 0 1rem 0;
        }
        .output-label {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-bottom: 0.25rem;
        }
        .output-value {
            color: #111827;
            font-size: 1.2rem;
            font-weight: 700;
            line-height: 1.3;
        }
        .memo-list {
            margin-top: 0.2rem;
            padding-left: 1.2rem;
        }
        div[data-testid="stSelectbox"] label {font-weight: 650;}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_demo_outputs(cache_version: str, scenario_items: tuple[tuple[str, object], ...]) -> dict[str, object]:
    _ = cache_version
    return run_pipeline(ROOT, scenario=dict(scenario_items), write_outputs=True)


def apply_posture_defaults() -> None:
    preset = st.session_state.get("policy_posture_preset", "Screening Mode")
    for key, value in POSTURE_DEFAULTS[preset].items():
        st.session_state[key] = value


def initialize_state() -> None:
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Executive View"
    if "policy_posture_preset" not in st.session_state:
        st.session_state.policy_posture_preset = "Screening Mode"
        apply_posture_defaults()
    for key, value in POSTURE_DEFAULTS[st.session_state.policy_posture_preset].items():
        st.session_state.setdefault(key, value)


def scenario_from_state() -> dict[str, object]:
    return {
        "policy_posture_preset": st.session_state.policy_posture_preset,
        "require_legal_low_risk_for_pilot": bool(st.session_state.require_legal_low_risk_for_pilot),
        "require_fiscal_data_for_pilot": bool(st.session_state.require_fiscal_data_for_pilot),
        "include_construction_stage_transition_candidates": bool(
            st.session_state.include_construction_stage_transition_candidates
        ),
        "minimum_data_confidence_band_for_pilot": str(st.session_state.minimum_data_confidence_band_for_pilot),
        "treat_unknown_developer_compliance_as_blocker": bool(
            st.session_state.treat_unknown_developer_compliance_as_blocker
        ),
    }


def render_header() -> str:
    nav_col, context_col = st.columns([0.22, 0.78], vertical_alignment="bottom")
    with nav_col:
        page = st.selectbox("View", PAGES, key="current_page")
    with context_col:
        st.markdown(
            "<div class='badge-row'>"
            "<span class='badge'>D5 fiscal cost analysis</span>"
            "<span class='badge'>D6 calibration analysis</span>"
            "<span class='badge'>D7 pilot design</span>"
            "<span class='badge warning'>Human review required</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='prototype-kicker'>Prototype v0.5-lite</div>", unsafe_allow_html=True)
    st.title(APP_TITLE)
    st.caption(APP_SUBTITLE)
    st.warning(WARNING_TEXT)
    return page


def metric_card(label: str, value: object, note: str = "") -> None:
    st.markdown(
        "<div class='metric-card'>"
        f"<div class='metric-label'>{html.escape(label)}</div>"
        f"<div class='metric-value'>{html.escape(str(value))}</div>"
        f"<div class='metric-note'>{html.escape(note)}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def note_card(title: str, lines: list[str]) -> None:
    body = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
    st.markdown(
        "<div class='note-card'>"
        f"<strong>{html.escape(title)}</strong>"
        f"<ul>{body}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )


def mapping_card(title: str, items: list[str]) -> None:
    body = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    st.markdown(
        "<div class='mapping-card'>"
        f"<strong>{html.escape(title)}</strong>"
        f"<ul>{body}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )


def filtered_options(series: pd.Series) -> list[str]:
    return sorted([str(value) for value in series.dropna().unique() if str(value).strip()])


def selected_or_all(label: str, options: list[str]) -> list[str]:
    return st.multiselect(label, options, default=options)


def format_gates(gates: object) -> str:
    parts = split_reason_codes(gates)
    if not parts or parts == ["none"]:
        return "None"
    return "; ".join(GATE_LABELS.get(part, part.replace("_", " ").title()) for part in parts)


def display_reason_text(text: str) -> str:
    replacements = {
        "Possible pilot screen candidate": "Potential pilot-review flag subject to validation",
        "No final fiscal support can be recommended": "Temporary transition support cannot be recommended",
        "Fiscal exposure missing": "Fiscal exposure placeholder",
        "D5/FBR/customs verification required": "D5/FBR/customs verification required",
    }
    output = str(text)
    for old, new in replacements.items():
        output = output.replace(old, new)
    return output


def decode_reason_codes(codes: object, reason_codes: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Reason Code": code, "Reason": display_reason_text(reason_codes.get(code, "Unmapped reason code"))}
            for code in split_reason_codes(codes)
        ]
    )


def activity_label(value: object) -> str:
    labels = {
        "operating_productive": "Reported production",
        "moving_toward_production": "Construction movement",
        "allotted_but_inactive": "Allotted, limited activity",
        "vacant_or_speculative": "Vacant or speculative",
        "unclear": "Unclear",
    }
    return labels.get(str(value), str(value).replace("_", " ").title())


def confidence_label(row: pd.Series) -> str:
    band = str(row.get("data_confidence_band", "")).replace("_", " ").title()
    score = row.get("data_confidence_score")
    try:
        return f"{band} ({float(score):.2f})"
    except (TypeError, ValueError):
        return band


def legal_label(value: object) -> str:
    value = str(value or "unknown").lower()
    if value == "high":
        return "D4 review high priority"
    if value in {"low", "medium"}:
        return f"D4 placeholder: {value}"
    return "D4 placeholder pending"


def fiscal_label(value: object) -> str:
    value = str(value or "unknown").lower()
    if value == "unknown":
        return "D5 exposure placeholder"
    return f"D5 exposure: {value}"


def treatment_label(text: object) -> str:
    output = str(text or "")
    if output == "More data required":
        return "More data required before fiscal/calibration use"
    replacements = {
        "Possible pilot screen candidate pending D4 legal review and D5 fiscal verification": (
            "Potential pilot-review candidate subject to D4/D5 validation"
        ),
        "Possible transition candidate": "Potential transition-review flag",
        "More data required before decision": "More data required before fiscal/calibration use",
        "Legal review required before any incentive treatment": "Legal review required before treatment screening",
        "No new temporary transition support, subject to D4/D5 verification": (
            "Unsuitable for new temporary transition support under current screen; D4/D5 validation required"
        ),
    }
    for old, new in replacements.items():
        output = output.replace(old, new)
    return output


def next_action_label(text: object) -> str:
    parts = [part.strip() for part in str(text or "").split("|") if part.strip()]
    if not parts:
        return "Human review required."
    return display_action_text(parts[0])


def display_action_text(text: object) -> str:
    output = str(text or "")
    replacements = {
        "contradictions": "cross-source/status conflicts",
        "policy screening": "fiscal/calibration screening",
        "pilot screen": "pilot-review screen",
    }
    for old, new in replacements.items():
        output = output.replace(old, new)
    return output


def display_memo_text(text: object) -> str:
    output = str(text or "")
    replacements = {
        "possible pilot screen candidate": "potential pilot-review candidate subject to validation",
        "pilot screen": "pilot-review screen",
    }
    for old, new in replacements.items():
        output = output.replace(old, new)
    return output


def split_pipe_text(text: object) -> list[str]:
    return [part.strip() for part in str(text or "").split("|") if part.strip()]


def render_bullets(items: list[str]) -> None:
    if not items:
        st.write("None identified by the prototype.")
        return
    st.markdown(
        "<ul class='memo-list'>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>",
        unsafe_allow_html=True,
    )


def output_card(label: str, value: object) -> None:
    st.markdown(
        "<div class='output-card'>"
        f"<div class='output-label'>{html.escape(label)}</div>"
        f"<div class='output-value'>{html.escape(str(value or 'Not available'))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def main_reason_codes(codes: object, limit: int = 5) -> str:
    parts = split_reason_codes(codes)
    if len(parts) > limit:
        return "; ".join(parts[:limit]) + f"; +{len(parts) - limit} more"
    return "; ".join(parts)


def recommendation_view(recommendations: pd.DataFrame) -> pd.DataFrame:
    view = recommendations.copy()
    view["hard_gates_display"] = view["hard_gates_triggered"].apply(format_gates)
    view["Reported Activity"] = view["activity_category"].apply(activity_label)
    view["Data Confidence"] = view.apply(confidence_label, axis=1)
    view["Legal Status"] = view["legal_status"] if "legal_status" in view.columns else view["legal_risk_level"].apply(legal_label)
    view["Fiscal Status"] = (
        view["fiscal_exposure_status"] if "fiscal_exposure_status" in view.columns else view["fiscal_exposure_level"].apply(fiscal_label)
    )
    view["Provisional Treatment"] = view["recommended_treatment"].apply(treatment_label)
    view["Main Reason Codes"] = view["reason_codes"].apply(main_reason_codes)
    view["Next Action"] = view["next_actions"].apply(next_action_label)
    return view


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


def high_confidence_count(summary: dict[str, Any]) -> int:
    counts = summary.get("confidence_band_counts", {})
    return int(counts.get("high", 0)) if isinstance(counts, dict) else 0


def canonical_field(value: object) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[\s/\-\.()]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def readable_field(field_name: str) -> str:
    overrides = {
        "cit_foregone": "CIT foregone",
        "fbr_source_reference": "FBR source reference",
        "kpi_period": "KPI period",
    }
    return overrides.get(field_name, field_name.replace("_", " ").title())


def required_fields_for(data_type: str) -> list[str]:
    return REQUIRED_FIELDS_BY_INTAKE_TYPE.get(data_type, [])


def intake_sample_frame(data_type: str, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    base_columns = ["zone_id", "zone_name"]
    base = frames["zones"][[column for column in base_columns if column in frames["zones"].columns]].head(5).copy()
    if base.empty:
        base = pd.DataFrame({"zone_id": [], "zone_name": []})
    for field in required_fields_for(data_type):
        if field not in base.columns:
            base[field] = ""
    base["source_file"] = base.get("source_file", "sample_mapping_template")
    base["validation_status"] = "template_preview"
    return base


def parse_uploaded_intake(uploaded_file: Any) -> tuple[pd.DataFrame | None, str]:
    if uploaded_file is None:
        return None, ""
    suffix = Path(uploaded_file.name).suffix.lower()
    try:
        if suffix == ".csv":
            return pd.read_csv(uploaded_file), ""
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(uploaded_file), ""
        return (
            pd.DataFrame(
                [
                    {
                        "file_name": uploaded_file.name,
                        "file_type": suffix.lstrip(".") or "unknown",
                        "parse_status": "metadata_only",
                    }
                ]
            ),
            "This file type is treated as unstructured evidence. It requires manual extraction, source checks, and owner validation before model outputs can be updated.",
        )
    except Exception as exc:  # pragma: no cover - Streamlit upload parsing depends on user files.
        return pd.DataFrame(), f"Upload could not be parsed for demo mapping: {exc}"


def analyze_intake_frame(
    df: pd.DataFrame,
    required_fields: list[str],
    existing_zones: pd.DataFrame,
    *,
    uploaded: bool,
    parse_note: str = "",
) -> dict[str, object]:
    canonical_columns = {canonical_field(column): column for column in df.columns}
    missing_required = [field for field in required_fields if canonical_field(field) not in canonical_columns]

    matched = 0
    if not df.empty and "zone_id" in canonical_columns and "zone_id" in existing_zones.columns:
        incoming = df[canonical_columns["zone_id"]].astype(str).str.strip()
        existing = set(existing_zones["zone_id"].astype(str).str.strip())
        matched = int(incoming.isin(existing).sum())
    elif not df.empty and "zone_name" in canonical_columns and "zone_name" in existing_zones.columns:
        incoming = df[canonical_columns["zone_name"]].astype(str).str.strip().str.lower()
        existing = set(existing_zones["zone_name"].astype(str).str.strip().str.lower())
        matched = int(incoming.isin(existing).sum())

    row_count = int(len(df))
    manual_review = max(row_count - matched, 0)
    if missing_required:
        manual_review = max(manual_review, row_count)

    if parse_note:
        outputs_update = "No - source extraction and validation are required first"
        validation_status = "Manual review required"
    elif not uploaded:
        outputs_update = "No - sample template only"
        validation_status = "Template preview"
    elif missing_required:
        outputs_update = "No - required fields are missing"
        validation_status = "Mapping review required"
    elif manual_review:
        outputs_update = "Partial - zone matching needs review"
        validation_status = "Manual review required"
    else:
        outputs_update = "Yes, after source checks and owner validation"
        validation_status = "Mapped, pending validation"

    field_rows = []
    required_lookup = {canonical_field(field): field for field in required_fields}
    for column in df.columns:
        canonical = canonical_field(column)
        field_rows.append(
            {
                "Field Detected": column,
                "Mapped Required Field": readable_field(required_lookup[canonical]) if canonical in required_lookup else "Not required for selected type",
            }
        )

    return {
        "fields_detected": pd.DataFrame(field_rows),
        "missing_required": missing_required,
        "matched_records": matched,
        "manual_review_records": manual_review,
        "outputs_update": outputs_update,
        "validation_status": validation_status,
        "parse_note": parse_note,
        "row_count": row_count,
    }


def required_data_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Data Category": "FBR / tax data",
                "Required Fields": "CIT foregone; customs exemptions; tax paid; incentive utilization",
                "Current Status": "Placeholder / missing pending D5 and FBR validation",
                "Why It Matters": "Needed to estimate fiscal exposure and avoid treating activity as proof of incentive effectiveness.",
                "Owner / Validator": "FBR / Finance",
            },
            {
                "Data Category": "Legal data",
                "Required Fields": "Development agreements; enterprise certificates; sunset clauses; change-in-law, arbitration, and compensation clauses",
                "Current Status": "Placeholder pending D4 legal review",
                "Why It Matters": "Determines whether phase-out, transition treatment, or enforcement review is legally constrained.",
                "Owner / Validator": "Legal team / BOI / SEZA",
            },
            {
                "Data Category": "Operational data",
                "Required Fields": "Plot-level status; production and construction dates; employment; exports; investment",
                "Current Status": "Structured screening dataset, not row-level verified enterprise evidence",
                "Why It Matters": "Drives activity classification, confidence scoring, and calibration readiness.",
                "Owner / Validator": "BOI / SEZA / developers / enterprises",
            },
            {
                "Data Category": "Infrastructure data",
                "Required Fields": "Electricity; gas; water; access roads; internal roads; wastewater; one-window / facilitation",
                "Current Status": "Partial screening fields available; utility evidence needs validation",
                "Why It Matters": "May explain underperformance and point toward non-fiscal facilitation rather than cost-based support.",
                "Owner / Validator": "BOI / SEZA / utilities / developers",
            },
            {
                "Data Category": "Customs / import-exemption data",
                "Required Fields": "Import exemption value; customs duty foregone; exemption type; goods category; tax year",
                "Current Status": "Missing pending FBR/customs source linkage",
                "Why It Matters": "Needed for fiscal exposure, benefit utilization, and phase-out risk review.",
                "Owner / Validator": "FBR / customs / Finance",
            },
            {
                "Data Category": "Verification / proxy data",
                "Required Fields": "Site visit date; utility-consumption proxy; production proxy; verifier; source reference",
                "Current Status": "Not loaded into current screening package",
                "Why It Matters": "Supports cross-source consistency checks before legal/fiscal/calibration decisions.",
                "Owner / Validator": "BOI / SEZA / REMIT / independent verifier",
            },
        ]
    )


def severity_label(value: object) -> str:
    return SEVERITY_LABELS.get(str(value or "").strip().lower(), "Caution")


def validation_display_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    if "issues" in frames and not frames["issues"].empty:
        parts.append(frames["issues"].assign(flag_group="Validation flag"))
    if "contradictions" in frames and not frames["contradictions"].empty:
        parts.append(frames["contradictions"].assign(flag_group="Cross-source/status conflict"))
    if not parts:
        return pd.DataFrame(
            columns=["Zone", "Field", "Validation Flag", "Severity", "Why It Matters", "Recommended Fix", "Source"]
        )

    combined = pd.concat(parts, ignore_index=True, sort=False)
    source_file = combined.get("source_file", pd.Series([""] * len(combined))).fillna("")
    source_row = combined.get("source_row", pd.Series([""] * len(combined))).fillna("")
    source = [
        "Consolidated SEZ source package" if not str(file_value).strip() else f"Consolidated SEZ source package; source row {row_value}".rstrip()
        for file_value, row_value in zip(source_file, source_row)
    ]
    return pd.DataFrame(
        {
            "Zone": combined.get("zone_name", pd.Series([""] * len(combined))).fillna("All zones"),
            "Field": combined.get("field_name", pd.Series([""] * len(combined))).fillna(""),
            "Validation Flag": combined.get("issue_description", pd.Series([""] * len(combined))).fillna(""),
            "Severity": combined.get("severity", pd.Series([""] * len(combined))).apply(severity_label),
            "Why It Matters": combined.get("model_impact", pd.Series([""] * len(combined))).fillna(""),
            "Recommended Fix": combined.get("recommended_fix", pd.Series([""] * len(combined))).fillna("Manual source review required."),
            "Source": source,
        }
    )


def validation_metric_counts(frames: dict[str, pd.DataFrame]) -> dict[str, int]:
    issues = frames.get("issues", pd.DataFrame())
    contradictions = frames.get("contradictions", pd.DataFrame())
    field_completeness = frames.get("field_completeness", pd.DataFrame())
    issue_text = issues.get("issue_type", pd.Series(dtype=str)).astype(str).str.lower()
    issue_desc = issues.get("issue_description", pd.Series(dtype=str)).astype(str).str.lower()
    contradiction_text = contradictions.get("issue_type", pd.Series(dtype=str)).astype(str).str.lower()
    contradiction_desc = contradictions.get("issue_description", pd.Series(dtype=str)).astype(str).str.lower()
    return {
        "missing_fields": int(issue_text.str.contains("missing", na=False).sum()),
        "coverage_warnings": int(
            contradiction_text.str.contains("scope|coverage|definition", regex=True, na=False).sum()
            + contradiction_desc.str.contains("universe|coverage|definition", regex=True, na=False).sum()
        ),
        "row_level_verification": int(
            issue_desc.str.contains("original workbook|source digest|source-row|source row", regex=True, na=False).sum()
        ),
        "fields_with_gaps": int((field_completeness.get("missing_count", pd.Series(dtype=int)).fillna(0) > 0).sum()),
    }


def friendly_dataframe(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    out = df.copy()
    if columns is not None:
        out = out[[column for column in columns if column in out.columns]]
    for column in ["dataset_name", "source_file"]:
        if column in out.columns:
            out[column] = out[column].apply(lambda value: "Structured screening dataset" if str(value).strip() else "")
    out = out.rename(columns={column: FIELD_LABELS.get(column, column.replace("_", " ").title()) for column in out.columns})
    out.columns = unique_column_names(list(out.columns))
    return out


def unique_column_names(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result: list[str] = []
    for column in columns:
        count = seen.get(column, 0)
        if count:
            result.append(f"{column} ({count + 1})")
        else:
            result.append(column)
        seen[column] = count + 1
    return result


def executive_table(display_recommendations: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "zone_id",
        "zone_name",
        "province",
        "Reported Activity",
        "Data Confidence",
        "Legal Status",
        "Fiscal Status",
        "Provisional Treatment",
        "Main Reason Codes",
        "Next Action",
    ]
    return display_recommendations[columns].rename(
        columns={
            "zone_id": "Zone ID",
            "zone_name": "Zone",
            "province": "Province",
        }
    )


def render_footer() -> None:
    st.markdown(
        f"<div class='footer-disclaimer'>{html.escape(FOOTER_TEXT)}</div>",
        unsafe_allow_html=True,
    )


def render_executive_view(frames: dict[str, pd.DataFrame], summary: dict[str, Any], display_recommendations: pd.DataFrame) -> None:
    st.markdown("### What This Tool Helps Answer")
    note_card(
        "Decision questions",
        [
            "Which zones need more data before fiscal or calibration use?",
            "Which zones require legal or contractual review?",
            "Which zones have reported production or construction movement?",
            "Which zones may be unsuitable for new fiscal support?",
            "Which zones may merit pilot review, subject to validation?",
            "What assumptions or data gaps drive the provisional result?",
        ],
    )

    st.markdown("### Executive Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Zones loaded", summary["zone_records_loaded"], "Structured screening dataset")
    with c2:
        metric_card("High-confidence records", high_confidence_count(summary), "Usable for demo triage")
    with c3:
        metric_card("Validation flags", summary["data_quality_issue_count"], "Open data checks")
    with c4:
        metric_card("Cross-source/status conflicts", summary["contradiction_count"], "Status or acreage conflicts")

    c5, c6, c7 = st.columns(3)
    with c5:
        metric_card("Legal/fiscal validation pending", review_count(frames["recommendations"]), "D4/D5 review trail")
    with c6:
        metric_card("Potential pilot-review flags", summary["possible_pilot_screen_candidates"], "Subject to validation")
    with c7:
        metric_card("More data required", summary["more_data_required"], "Before fiscal/calibration use")

    st.markdown("### Executive Triage Table")
    st.dataframe(executive_table(display_recommendations), width="stretch", hide_index=True)

    st.markdown("### D5 / D6 / D7 Mapping")
    d5, d6, d7 = st.columns(3)
    with d5:
        mapping_card(
            "D5 Fiscal Cost Analysis",
            [
                "fiscal exposure matrix",
                "assumptions log",
                "data gaps",
                "sensitivity scenarios",
                "zone-wise cost/risk flags",
            ],
        )
    with d6:
        mapping_card(
            "D6 Calibration Analysis",
            [
                "legal/compliance gates",
                "eligibility logic",
                "support caps / sunset / audit triggers",
                "cost-based support scenarios",
                "reason-coded treatment categories",
            ],
        )
    with d7:
        mapping_card(
            "D7 Pilot Design",
            [
                "pilot-review flags",
                "implementation readiness",
                "KPI / monitoring needs",
                "legal/fiscal validation prerequisites",
            ],
        )


def render_zone_explorer(frames: dict[str, pd.DataFrame], display_recommendations: pd.DataFrame) -> None:
    st.markdown("### Zone Explorer")
    explorer = display_recommendations.merge(
        frames["zones"],
        on=["zone_id", "zone_name", "province", "operational_status"],
        how="left",
        suffixes=("", "_source"),
    )

    c1, c2, c3, c4 = st.columns(4)
    province_filter = c1.multiselect(
        "Province", filtered_options(explorer["province"]), default=filtered_options(explorer["province"])
    )
    activity_filter = c2.multiselect(
        "Reported Activity",
        filtered_options(explorer["Reported Activity"]),
        default=filtered_options(explorer["Reported Activity"]),
    )
    confidence_filter = c3.multiselect(
        "Data Confidence",
        filtered_options(explorer["Data Confidence"]),
        default=filtered_options(explorer["Data Confidence"]),
    )
    treatment_filter = c4.multiselect(
        "Provisional Treatment",
        filtered_options(explorer["Provisional Treatment"]),
        default=filtered_options(explorer["Provisional Treatment"]),
    )

    filtered = explorer[
        explorer["province"].isin(province_filter)
        & explorer["Reported Activity"].isin(activity_filter)
        & explorer["Data Confidence"].isin(confidence_filter)
        & explorer["Provisional Treatment"].isin(treatment_filter)
    ]

    st.dataframe(
        filtered[
            [
                "zone_id",
                "zone_name",
                "province",
                "Reported Activity",
                "Data Confidence",
                "Provisional Treatment",
                "hard_gates_display",
            ]
        ].rename(
            columns={
                "zone_id": "Zone ID",
                "zone_name": "Zone",
                "province": "Province",
                "hard_gates_display": "Hard Gates",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    selected = st.selectbox("Selected zone", filtered["zone_name"].tolist() if not filtered.empty else [])
    if selected:
        rec = filtered[filtered["zone_name"] == selected].iloc[0]
        st.markdown("### Selected Zone Brief")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Reported Activity", rec["Reported Activity"])
        c2.metric("Data Confidence", rec["Data Confidence"])
        c3.metric("Legal Status", rec["Legal Status"])
        c4.metric("Fiscal Status", rec["Fiscal Status"])
        st.write(rec["Provisional Treatment"])

        detail_columns = [
            "zone_id",
            "zone_name",
            "province",
            "developer_name",
            "developer_mode",
            "zone_type",
            "operational_status",
            "total_area_acres",
            "industrial_area_acres",
            "allotted_area_acres",
            "vacant_area_acres",
            "under_construction_area_acres",
            "under_production_area_acres",
            "unsold_area_acres",
            "number_allottees",
            "electricity_status",
            "gas_status",
            "water_status",
            "wastewater_status",
            "roads_status",
            "Data Confidence",
            "Reported Activity",
            "Provisional Treatment",
            "hard_gates_display",
            "reason_codes",
            "source_file",
            "source_row",
        ]
        with st.expander("Detailed source fields and raw screening trace"):
            st.dataframe(friendly_dataframe(filtered[filtered["zone_name"] == selected], detail_columns), width="stretch", hide_index=True)


def render_recommendation_engine(
    frames: dict[str, pd.DataFrame],
    reason_codes: dict[str, str],
    recommendations: pd.DataFrame,
    display_recommendations: pd.DataFrame,
) -> None:
    st.markdown("### Recommendation Engine")
    st.caption("Reason-coded provisional screening logic. Human, D4 legal, and D5 fiscal review remain mandatory.")

    st.dataframe(
        executive_table(display_recommendations),
        width="stretch",
        hide_index=True,
    )

    selected = st.selectbox("Selected zone for explanation", recommendations["zone_name"].tolist())
    rec = recommendations[recommendations["zone_name"] == selected].iloc[0]
    display_rec = display_recommendations[display_recommendations["zone_id"] == rec["zone_id"]].iloc[0]

    st.markdown("### Selected Zone Card")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zone", rec["zone_name"])
    c2.metric("Province", rec["province"])
    c3.metric("Reported Status", str(rec.get("operational_status", "Unknown"))[:42])
    c4.metric("Activity Category", activity_label(rec["activity_category"]))

    c5, c6, c7 = st.columns(3)
    c5.metric("Data Confidence", display_rec["Data Confidence"])
    c6.metric("Legal Status", rec.get("legal_status", display_rec["Legal Status"]))
    c7.metric("Fiscal Status", rec.get("fiscal_exposure_status", display_rec["Fiscal Status"]))

    st.info(
        "Reported activity is not treated as proof that incentives caused the activity. "
        "Additionality and net fiscal/economic impact require separate validation."
    )

    c8, c9, c10 = st.columns(3)
    c8.metric("Additionality Confidence", rec.get("additionality_confidence", "Unknown"))
    c9.metric("Incentive-Effectiveness Confidence", rec.get("incentive_effectiveness_confidence", "Unknown"))
    c10.metric("Net Fiscal/Economic Impact", rec.get("net_fiscal_economic_impact", "Unknown"))

    c11, c12, c13 = st.columns(3)
    c11.metric("Fiscal Exposure Status", rec.get("fiscal_exposure_status", "Missing"))
    c12.metric("Compliance Status", rec.get("compliance_status", "Requires validation"))
    c13.metric("Human Review", rec.get("human_review_status", "Required"))

    st.markdown("### Provisional Output")
    o1, o2 = st.columns(2)
    with o1:
        output_card("Provisional treatment", rec.get("provisional_treatment", rec.get("recommended_treatment", "")))
    with o2:
        output_card("Illustrative support treatment", rec.get("illustrative_support_treatment", ""))
    output_card("Illustrative instrument options", rec.get("illustrative_instrument_options", "None"))

    st.markdown("### Why")
    st.write(display_memo_text(rec.get("why", "")))

    st.markdown("### Blocking Validation Requirements")
    render_bullets(split_pipe_text(rec.get("blocking_validation_requirements", "")))

    st.markdown("### Main Reason Codes")
    st.dataframe(decode_reason_codes(rec["reason_codes"], reason_codes), width="stretch", hide_index=True)

    st.markdown("### Data Gaps")
    render_bullets(split_pipe_text(rec.get("data_gaps", "")))

    c14, c15 = st.columns(2)
    with c14:
        st.markdown("### Next Required Action")
        st.write(display_action_text(rec.get("next_actions", "Human review required.")))
    with c15:
        st.markdown("### Validator / Owner")
        st.write(rec.get("validator_owner", "BOI / SEZA / FBR / Finance / legal team / REMIT"))

    st.markdown("### Human Review")
    st.write("Required")

    with st.expander("Audit trail / technical details"):
        st.markdown("#### Gates and Scoring")
        scoring = pd.DataFrame(
            [
                {
                    "Data Confidence Score": rec.get("data_confidence_score"),
                    "Data Confidence Band": rec.get("data_confidence_band"),
                    "Hard Gates": format_gates(rec.get("hard_gates_triggered")),
                    "Reason Codes": rec.get("reason_codes"),
                    "Validator / Owner": rec.get("validator_owner"),
                }
            ]
        )
        st.dataframe(scoring, width="stretch", hide_index=True)

        st.markdown("#### Raw Recommendation Record")
        raw = pd.DataFrame([rec.to_dict()])
        raw["recommended_treatment"] = display_rec["Provisional Treatment"]
        st.dataframe(friendly_dataframe(raw), width="stretch", hide_index=True)

        source = frames["zones"][frames["zones"]["zone_id"] == rec["zone_id"]]
        if not source.empty:
            st.markdown("#### Source Fields")
            st.dataframe(friendly_dataframe(source), width="stretch", hide_index=True)


def render_data_intake(frames: dict[str, pd.DataFrame], summary: dict[str, Any]) -> None:
    st.markdown("### Data Intake")
    st.caption(
        "Use this page to map additional BOI, SEZA, FBR, Finance, legal, developer, enterprise, "
        "and verification data into the screening framework. Uploaded data is not treated as validated "
        "until required fields and source checks are complete."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zone records", summary["zone_records_loaded"])
    c2.metric("Detected source records", summary["detected_zone_profile_records_from_source_digest"])
    c3.metric("Structured indicator records", summary["normalized_indicator_records_from_source_digest"])
    c4.metric("Placeholder tables", "Created" if summary.get("placeholders_created") else "Present")

    note_card(
        "Source package note",
        [
            "The current source package is suitable for screening and demonstration. Exact row-level verification should use the original workbook and source documents before policy use.",
            "The current structured screening dataset covers 35 detected zone profile records and 35 indicator records based on the source digest.",
            "Legal, enterprise compliance, and fiscal exposure fields remain placeholders pending D4/D5 validation.",
        ],
    )

    st.markdown("### Incoming Data Mapping")
    data_type = st.selectbox("Data type", DATA_INTAKE_TYPES)
    uploaded_file = st.file_uploader(
        "Upload structured file for mapping review",
        type=["csv", "xlsx", "xls", "pdf", "docx"],
        help="CSV and Excel files are parsed for demo field mapping. PDF/DOCX uploads are treated as evidence that requires manual extraction.",
    )
    use_sample = st.checkbox("Use sample mapping template when no file is uploaded", value=True)

    parsed, parse_note = parse_uploaded_intake(uploaded_file)
    if parsed is None and use_sample:
        parsed = intake_sample_frame(data_type, frames)
    elif parsed is None:
        parsed = pd.DataFrame()

    analysis = analyze_intake_frame(
        parsed,
        required_fields_for(data_type),
        frames["zones"],
        uploaded=uploaded_file is not None,
        parse_note=parse_note,
    )

    if parse_note:
        st.warning(parse_note)
    elif uploaded_file is None:
        st.info("No uploaded file is being ingested. The table below is a mapping template preview only.")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Fields detected", len(parsed.columns))
    m2.metric("Missing required fields", len(analysis["missing_required"]))
    m3.metric("Records matched to zones", analysis["matched_records"])
    m4.metric("Manual review records", analysis["manual_review_records"])
    m5.metric("Validation status", analysis["validation_status"])

    c5, c6 = st.columns([0.58, 0.42])
    with c5:
        st.markdown("#### Fields Detected")
        st.dataframe(analysis["fields_detected"], width="stretch", hide_index=True)
    with c6:
        st.markdown("#### Mapping Result")
        st.write(f"Whether model outputs can be updated: **{analysis['outputs_update']}**")
        missing = [readable_field(field) for field in analysis["missing_required"]]
        if missing:
            render_bullets(missing)
        else:
            st.write("No required fields are missing for the selected intake type.")

    with st.expander("Mapped data preview"):
        st.dataframe(friendly_dataframe(parsed.head(25)), width="stretch", hide_index=True)

    st.markdown("### Required-Data Matrix")
    st.dataframe(required_data_matrix(), width="stretch", hide_index=True)

    st.markdown("### D5 Fiscal Exposure Intake")
    fiscal = frames["fiscal"].merge(
        frames["recommendations"][["zone_id", "zone_name", "fiscal_exposure_level", "required_fbr_action"]],
        on=["zone_id", "zone_name", "fiscal_exposure_level"],
        how="left",
    )
    st.dataframe(friendly_dataframe(fiscal), width="stretch", hide_index=True)

    with st.expander("Audit trail / technical details"):
        assumptions = pd.DataFrame(
            [
                {
                    "Assumption": "Fiscal exposure fields are placeholders",
                    "Decision Connection": "D5/FBR/customs verification required before fiscal-cost or support review.",
                },
                {
                    "Assumption": "Legal status fields are placeholders",
                    "Decision Connection": "D4 legal review required before treatment screening or phase-out analysis.",
                },
                {
                    "Assumption": "Current source package is a 35-zone structured screening dataset",
                    "Decision Connection": "Not the final reconciled 44/54-zone universe; denominators and coverage need reconciliation.",
                },
                {
                    "Assumption": "Cost-based support is temporary transition support only",
                    "Decision Connection": "All SEZ fiscal incentives phase out by 30 June 2035.",
                },
            ]
        )
        st.dataframe(assumptions, width="stretch", hide_index=True)

    with st.expander("Structured screening dataset preview"):
        st.dataframe(friendly_dataframe(frames["zones"]), width="stretch", hide_index=True)


def render_data_validation(frames: dict[str, pd.DataFrame], summary: dict[str, Any]) -> None:
    st.markdown("### Data Validation & Source Confidence")
    st.warning(
        "The current source package is suitable for screening and demonstration. Exact row-level verification should use "
        "the original workbook and source documents before policy use."
    )
    st.caption(
        "Validation flags are source-confidence and mapping checks, not app errors. They show which data gaps affect "
        "legal review, fiscal verification, calibration readiness, and pilot-review screening."
    )

    counts = validation_metric_counts(frames)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Validation flags", summary["data_quality_issue_count"])
    c2.metric("Cross-source/status conflicts", summary["contradiction_count"])
    c3.metric("Missing field checks", counts["missing_fields"])
    c4.metric("Coverage / definition warnings", counts["coverage_warnings"])
    c5.metric("Row-level verification fields", counts["row_level_verification"])

    st.markdown("### Source Confidence Summary")
    severity_counts = validation_display_table(frames)["Severity"].value_counts().rename_axis("Severity").reset_index(
        name="Validation Flags"
    )
    st.dataframe(severity_counts, width="stretch", hide_index=True)

    note_card(
        "Decision connection",
        [
            "Missing legal fields block D4 treatment screening and phase-out analysis.",
            "Missing fiscal/FBR/customs fields block fiscal exposure estimates and cost-based transition review.",
            "Missing operational and enterprise fields weaken activity classification, additionality review, and calibration confidence.",
            "Coverage / definition warnings mean the 35-zone structured screening dataset should not be generalized to the full 44/54-zone universe without reconciliation.",
        ],
    )

    st.markdown("### Validation Flags")
    validation_table = validation_display_table(frames)
    severity_filter = st.multiselect(
        "Severity",
        ["Blocking", "Material", "Caution", "Info"],
        default=["Blocking", "Material", "Caution", "Info"],
    )
    filtered_validation = validation_table[validation_table["Severity"].isin(severity_filter)]
    st.dataframe(filtered_validation, width="stretch", hide_index=True)

    st.markdown("### Data-Confidence Scoring")
    scoring = pd.DataFrame(
        [
            {"Component": "Source reliability", "Use in Score": "Checks whether source lineage is present and credible."},
            {"Component": "Completeness", "Use in Score": "Checks critical fields needed for screening and validation."},
            {"Component": "Internal consistency", "Use in Score": "Checks acreage, status, and field-level logic within a record."},
            {"Component": "Cross-source consistency", "Use in Score": "Checks conflicts across source package, status fields, and coverage notes."},
            {"Component": "Recency", "Use in Score": "Checks whether current-period source notes are present."},
        ]
    )
    banding = pd.DataFrame(
        [
            {"Band": "High", "Use": "Can support demo screening, still subject to source-row validation."},
            {"Band": "Medium", "Use": "Can support cautious demo triage with validation caveats."},
            {"Band": "Low", "Use": "Use only for preliminary source repair and gap review."},
            {"Band": "Do not use for decision", "Use": "Do not use for legal, fiscal, incentive, or calibration decisions."},
        ]
    )
    c6, c7 = st.columns(2)
    c6.dataframe(scoring, width="stretch", hide_index=True)
    c7.dataframe(banding, width="stretch", hide_index=True)

    st.markdown("### Source Lineage")
    lineage_columns = ["zone_id", "zone_name", "source_file", "source_row"]
    lineage = frames["zones"][[column for column in lineage_columns if column in frames["zones"].columns]].copy()
    st.dataframe(friendly_dataframe(lineage), width="stretch", hide_index=True)

    with st.expander("Audit trail / technical details"):
        st.metric("Fields with missing values", counts["fields_with_gaps"])
        st.dataframe(friendly_dataframe(frames["field_completeness"]), width="stretch", hide_index=True)
        st.dataframe(friendly_dataframe(frames["confidence"]), width="stretch", hide_index=True)

    with st.expander("Source processing log"):
        processing_log = pd.DataFrame(
            [
                {
                    "Processing Step": "Load consolidated SEZ source package",
                    "Status": f"{summary['zone_records_loaded']} zone records loaded for screening.",
                },
                {
                    "Processing Step": "Apply validation checks",
                    "Status": f"{summary['data_quality_issue_count']} validation flags generated.",
                },
                {
                    "Processing Step": "Check cross-source/status conflicts",
                    "Status": f"{summary['contradiction_count']} conflicts or coverage warnings generated.",
                },
                {
                    "Processing Step": "Generate confidence bands",
                    "Status": "High / Medium / Low / Do not use for decision bands calculated from source reliability, completeness, consistency, and recency.",
                },
            ]
        )
        st.dataframe(processing_log, width="stretch", hide_index=True)

    with st.expander("Raw validation output"):
        st.markdown("#### Raw validation flags")
        st.dataframe(friendly_dataframe(frames["issues"]), width="stretch", hide_index=True)
        st.markdown("#### Raw cross-source/status conflicts")
        st.dataframe(friendly_dataframe(frames["contradictions"]), width="stretch", hide_index=True)
        st.markdown("#### Raw field completeness")
        st.dataframe(friendly_dataframe(frames["field_completeness"]), width="stretch", hide_index=True)


def kpi_need(row: pd.Series) -> str:
    activity = str(row.get("activity_category", ""))
    if activity == "operating_productive":
        return "Verify production, employment, exports, utility uptime, and fiscal exposure."
    if activity == "moving_toward_production":
        return "Track construction milestones, energization, allottee readiness, and start-of-production evidence."
    if activity == "vacant_or_speculative":
        return "Review land use, allotment status, vacancy drivers, and cure/enforcement options."
    if activity == "allotted_but_inactive":
        return "Verify allotment progress, enterprise status, and non-fiscal facilitation needs."
    return "Request missing operational, enterprise, and source-lineage evidence."


def readiness_label(row: pd.Series) -> str:
    band = str(row.get("data_confidence_band", ""))
    activity = str(row.get("activity_category", ""))
    if band in {"medium", "high"} and activity == "operating_productive":
        return "Monitoring-ready subject to D4/D5 validation"
    if activity == "moving_toward_production":
        return "Transition monitoring needed"
    if band in {"low", "do_not_use"}:
        return "Evidence not ready"
    return "Human review needed"


def render_kpi_assurance(frames: dict[str, pd.DataFrame]) -> None:
    st.markdown("### KPI Assurance")
    st.caption("KPI and monitoring readiness view for D7 pilot design and implementation assurance.")

    kpi = frames["zones"].merge(frames["activity"], on=["zone_id", "zone_name"], how="left")
    kpi = kpi.merge(frames["confidence"], on=["zone_id", "zone_name"], how="left")
    kpi["Readiness"] = kpi.apply(readiness_label, axis=1)
    kpi["KPI / Monitoring Need"] = kpi.apply(kpi_need, axis=1)
    kpi["Reported Activity"] = kpi["activity_category"].apply(activity_label)
    kpi["Data Confidence"] = kpi.apply(confidence_label, axis=1)

    note_card(
        "KPI assurance focus",
        [
            "Production evidence and enterprise activity",
            "Construction milestones and utility readiness",
            "Land-use efficiency and vacancy/unsold land signals",
            "Fiscal exposure, customs/FBR data, and audit trail readiness",
            "D4/D5 validation prerequisites before any pilot-review use",
        ],
    )

    columns = [
        "zone_id",
        "zone_name",
        "province",
        "Reported Activity",
        "Data Confidence",
        "under_production_area_acres",
        "under_construction_area_acres",
        "vacant_area_acres",
        "Readiness",
        "KPI / Monitoring Need",
    ]
    st.dataframe(friendly_dataframe(kpi, columns), width="stretch", hide_index=True)


def render_scenario_settings(summary: dict[str, Any]) -> None:
    st.markdown("### Advanced Model Settings")
    st.caption("Demo assumptions only. These settings do not represent final policy.")

    c1, c2 = st.columns(2)
    with c1:
        st.selectbox(
            "Policy posture preset",
            list(POSTURE_DEFAULTS),
            key="policy_posture_preset",
            on_change=apply_posture_defaults,
        )
        st.checkbox(
            "Only show low-legal-risk zones as pilot-review flags",
            key="require_legal_low_risk_for_pilot",
        )
        st.checkbox(
            "Require D5 fiscal data before pilot-review screening",
            key="require_fiscal_data_for_pilot",
        )
        st.checkbox(
            "Include construction-stage zones as transition-review flags",
            key="include_construction_stage_transition_candidates",
        )
        st.selectbox(
            "Minimum data-confidence band for pilot-review flag",
            CONFIDENCE_BANDS,
            key="minimum_data_confidence_band_for_pilot",
        )
        st.checkbox(
            "Treat unknown developer compliance as blocker",
            key="treat_unknown_developer_compliance_as_blocker",
        )

    with c2:
        note_card(
            "Current assumption set",
            [
                f"Posture: {st.session_state.policy_posture_preset}",
                f"Minimum confidence: {st.session_state.minimum_data_confidence_band_for_pilot}",
                f"Potential pilot-review flags: {summary['possible_pilot_screen_candidates']}",
                f"More data required: {summary['more_data_required']}",
                "All outputs remain provisional and subject to D4 legal review and D5 fiscal verification.",
                "Cost-based support is temporary transition support only and all SEZ fiscal incentives phase out by 30 June 2035.",
            ],
        )


def render_export() -> None:
    st.markdown("### Export")
    st.caption("Download generated screening outputs for review, audit, or offline analysis.")

    output_dir = ROOT / "outputs"
    export_files = [
        ("zone_triage_prototype.csv", "Download executive triage table"),
        ("recommendation_explanations.csv", "Download recommendation explanations"),
        ("audit_flags.csv", "Download audit flags"),
        ("data_quality_issue_log.csv", "Download validation flags"),
        ("contradiction_log.csv", "Download cross-source/status conflicts"),
        ("data_confidence_scores.csv", "Download confidence scores"),
        ("activity_classification.csv", "Download activity classification"),
        ("field_completeness.csv", "Download field completeness"),
        ("summary.json", "Download summary JSON"),
        ("sez_calibration_demo_outputs.xlsx", "Download Excel output package"),
    ]

    for name, label in export_files:
        path = output_dir / name
        if path.exists():
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if name.endswith(".xlsx") else "text/csv"
            if name.endswith(".json"):
                mime = "application/json"
            st.download_button(
                label=label,
                data=path.read_bytes(),
                file_name=name,
                mime=mime,
            )


inject_css()
initialize_state()
model_settings = scenario_from_state()
result = load_demo_outputs(UI_CACHE_VERSION, tuple(sorted(model_settings.items())))
frames: dict[str, pd.DataFrame] = result["frames"]
summary: dict[str, object] = result["summary"]
reason_codes = load_reason_codes(ROOT / "config" / "reason_codes_v0_5_lite.yaml")
recommendations = frames["recommendations"]
display_recommendations = recommendation_view(recommendations)

page = render_header()

if page == "Executive View":
    render_executive_view(frames, summary, display_recommendations)
elif page == "Zone Explorer":
    render_zone_explorer(frames, display_recommendations)
elif page == "Recommendation Engine":
    render_recommendation_engine(frames, reason_codes, recommendations, display_recommendations)
elif page == "Data Intake":
    render_data_intake(frames, summary)
elif page == "Data Validation & Source Confidence":
    render_data_validation(frames, summary)
elif page == "KPI Assurance":
    render_kpi_assurance(frames)
elif page == "Advanced Model Settings":
    render_scenario_settings(summary)
elif page == "Export":
    render_export()

render_footer()
