from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import html
import os
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
from sez_calibration.recommendation_engine import (  # noqa: E402
    INSTRUMENT_OPTIONS,
    PROVISIONAL_TREATMENTS,
    SUPPORT_TREATMENTS,
    load_reason_codes,
    run_recommendation_engine,
)
from sez_calibration.ui_copy import (  # noqa: E402
    APP_SUBTITLE,
    APP_TITLE,
    DATA_PROFILE_LABEL,
    DATASET_BASIS_LABEL,
    HUMAN_REVIEW_LABEL,
    NON_DECISION_STATEMENT,
    REAL_USE_REQUIREMENTS,
)


APP_VERSION = "prototype-demo-v0.8"
WARNING_TEXT = NON_DECISION_STATEMENT
ADDITIONALITY_NOTE = (
    "Reported production or construction is not treated as proof of incentive effectiveness. "
    "Additionality and net fiscal/economic impact require separate validation."
)
FOOTER_TEXT = "Prototype screening output. Human review required."
DATA_MODE_OPTIONS = [
    "Synthetic demo data",
    "Restricted internal dataset",
    "Verified source-cleared data",
]
DATA_MODE_WARNING = "Warning: confirm that this dataset is cleared for use in this environment before sharing the app link."
PUBLIC_LINK_WARNING = (
    "Do not share a public link containing non-public BOI, SEZA, FBR, Finance, legal, developer, or enterprise data "
    "unless hosted in an authorized environment."
)
SOURCE_PERMISSION_WARNING = "Source data may require permission before external circulation."
REASON_CODES_FILE = ROOT / "config" / "reason_codes_v0_5_lite.yaml"
UI_CACHE_VERSION = APP_VERSION
SHOW_ADVANCED_SCENARIOS = os.getenv("SHOW_ADVANCED_SCENARIOS") == "1"

PAGES = [
    "Executive Triage",
    "Case Review",
    "Data Confidence",
    "Export",
    "About / Limitations",
]
if SHOW_ADVANCED_SCENARIOS:
    PAGES.append("Scenario Settings")
CONFIDENCE_BANDS = ["low", "medium", "high"]
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
DEMO_SCRIPT_STEPS = [
    "This is the executive triage view.",
    "The tool does not make final decisions; it shows provisional treatment categories.",
    "This example shows reported activity, but legal and fiscal validation are still required.",
    "This example shows how low data confidence blocks policy use.",
    "This example shows how assumptions change the output.",
    "The output can be exported as a short screening note.",
]
DEMO_CASE_DEFINITIONS = [
    {
        "key": "zone_a",
        "anonymous_label": "Zone A \u2014 reported production / high confidence",
        "selector_note": "reported-production case",
    },
    {
        "key": "zone_b",
        "anonymous_label": "Zone B \u2014 construction movement / validation needed",
        "selector_note": "construction-stage case",
    },
    {
        "key": "zone_c",
        "anonymous_label": "Zone C \u2014 low data confidence / more data required",
        "selector_note": "source-confidence case",
    },
    {
        "key": "zone_d",
        "anonymous_label": "Zone D \u2014 legal/fiscal review required",
        "selector_note": "legal/fiscal validation case",
    },
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
SCENARIO_PRESETS = {
    "IMF strict triage": {
        "behavior": "Strong legal, compliance, fiscal-data, and data-confidence gates.",
        "weights": {"legal": "high", "compliance": "high", "fiscal": "high", "data_quality": "high", "growth_continuity": "low"},
        "gates": {
            "require_legal_low_risk_for_pilot": True,
            "require_fiscal_data_for_pilot": True,
            "block_high_fiscal_exposure": True,
            "include_construction_stage_transition_candidates": False,
            "minimum_data_confidence_band_for_pilot": "high",
            "strict_data_confidence_for_all": True,
            "treat_unknown_developer_compliance_as_blocker": True,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": False,
        },
    },
    "Legal-risk conservative": {
        "behavior": "High or not-yet-validated legal risk pushes output to legal review / transition review.",
        "weights": {"legal": "high", "compliance": "medium", "fiscal": "medium", "data_quality": "medium", "growth_continuity": "low"},
        "gates": {
            "require_legal_low_risk_for_pilot": True,
            "require_fiscal_data_for_pilot": False,
            "block_high_fiscal_exposure": False,
            "include_construction_stage_transition_candidates": True,
            "minimum_data_confidence_band_for_pilot": "medium",
            "strict_data_confidence_for_all": False,
            "treat_unknown_developer_compliance_as_blocker": False,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": False,
        },
    },
    "Fiscal-risk conservative": {
        "behavior": "Missing or high fiscal exposure blocks cost-based support-review language.",
        "weights": {"legal": "medium", "compliance": "medium", "fiscal": "high", "data_quality": "medium", "growth_continuity": "low"},
        "gates": {
            "require_legal_low_risk_for_pilot": False,
            "require_fiscal_data_for_pilot": True,
            "block_high_fiscal_exposure": True,
            "include_construction_stage_transition_candidates": True,
            "minimum_data_confidence_band_for_pilot": "medium",
            "strict_data_confidence_for_all": False,
            "treat_unknown_developer_compliance_as_blocker": False,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": False,
        },
    },
    "Data-quality conservative": {
        "behavior": "Low/medium confidence pushes to more data required.",
        "weights": {"legal": "medium", "compliance": "medium", "fiscal": "medium", "data_quality": "high", "growth_continuity": "low"},
        "gates": {
            "require_legal_low_risk_for_pilot": False,
            "require_fiscal_data_for_pilot": False,
            "block_high_fiscal_exposure": False,
            "include_construction_stage_transition_candidates": True,
            "minimum_data_confidence_band_for_pilot": "high",
            "strict_data_confidence_for_all": True,
            "treat_unknown_developer_compliance_as_blocker": False,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": False,
        },
    },
    "Growth-preserving transition": {
        "behavior": "Gives some weight to production/construction movement but keeps legal/fiscal validation caveats.",
        "weights": {"legal": "medium", "compliance": "medium", "fiscal": "medium", "data_quality": "medium", "growth_continuity": "high"},
        "gates": {
            "require_legal_low_risk_for_pilot": False,
            "require_fiscal_data_for_pilot": False,
            "block_high_fiscal_exposure": False,
            "include_construction_stage_transition_candidates": True,
            "minimum_data_confidence_band_for_pilot": "medium",
            "strict_data_confidence_for_all": False,
            "treat_unknown_developer_compliance_as_blocker": False,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": False,
        },
    },
    "Pilot-readiness screen": {
        "behavior": "Emphasizes operational readiness, data confidence, verification feasibility, and pilot learning value.",
        "weights": {"legal": "medium", "compliance": "medium", "fiscal": "medium", "data_quality": "high", "pilot_learning": "high"},
        "gates": {
            "require_legal_low_risk_for_pilot": True,
            "require_fiscal_data_for_pilot": False,
            "block_high_fiscal_exposure": True,
            "include_construction_stage_transition_candidates": False,
            "minimum_data_confidence_band_for_pilot": "high",
            "strict_data_confidence_for_all": False,
            "treat_unknown_developer_compliance_as_blocker": True,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": False,
        },
    },
    "Non-fiscal support emphasis": {
        "behavior": "Directs weak additionality/high fiscal exposure cases toward non-fiscal support.",
        "weights": {"legal": "medium", "compliance": "medium", "fiscal": "high", "data_quality": "medium", "non_fiscal": "high"},
        "gates": {
            "require_legal_low_risk_for_pilot": False,
            "require_fiscal_data_for_pilot": False,
            "block_high_fiscal_exposure": False,
            "include_construction_stage_transition_candidates": True,
            "minimum_data_confidence_band_for_pilot": "medium",
            "strict_data_confidence_for_all": False,
            "treat_unknown_developer_compliance_as_blocker": False,
            "prefer_non_fiscal_when_additionality_uncertain": True,
            "diagnostic_only": False,
        },
    },
    "Broad diagnostic screen": {
        "behavior": "Allows wider screening flags, but labels them as diagnostic only.",
        "weights": {"legal": "low", "compliance": "low", "fiscal": "low", "data_quality": "low", "diagnostic_learning": "high"},
        "gates": {
            "require_legal_low_risk_for_pilot": False,
            "require_fiscal_data_for_pilot": False,
            "block_high_fiscal_exposure": False,
            "include_construction_stage_transition_candidates": True,
            "minimum_data_confidence_band_for_pilot": "low",
            "strict_data_confidence_for_all": False,
            "treat_unknown_developer_compliance_as_blocker": False,
            "prefer_non_fiscal_when_additionality_uncertain": False,
            "diagnostic_only": True,
        },
    },
}
POSTURE_DEFAULTS = {name: config["gates"] for name, config in SCENARIO_PRESETS.items()}
OUTPUT_CATEGORIES = {
    "provisional_treatments": tuple(PROVISIONAL_TREATMENTS.values()),
    "illustrative_support_treatments": tuple(SUPPORT_TREATMENTS.values()),
    "illustrative_instrument_options": tuple(INSTRUMENT_OPTIONS.values()),
}
DATA_MODES = {
    "data_mode_options": tuple(DATA_MODE_OPTIONS),
    "pages": tuple(PAGES),
    "intake_types": tuple(DATA_INTAKE_TYPES),
    "confidence_bands": ("High", "Medium", "Low", "Do not use for decision"),
    "advanced_setting_confidence_choices": tuple(CONFIDENCE_BANDS),
    "validation_severity_labels": tuple(dict.fromkeys(SEVERITY_LABELS.values())),
}
APP_CONFIG = {
    "version": APP_VERSION,
    "title": APP_TITLE,
    "subtitle": APP_SUBTITLE,
    "warning_banner": WARNING_TEXT,
    "additionality_note": ADDITIONALITY_NOTE,
    "footer": FOOTER_TEXT,
    "output_categories": OUTPUT_CATEGORIES,
    "reason_codes_file": REASON_CODES_FILE,
    "scenario_presets": SCENARIO_PRESETS,
    "data_modes": DATA_MODES,
}

FIELD_LABELS = {
    "zone_id": "Zone ID",
    "zone_name": "Zone",
    "province": "Province",
    "developer_name": "Developer",
    "developer_mode": "Developer Mode",
    "zone_type": "Zone Type",
    "operational_status": "Reported Operational Status",
    "total_area_acres": "Total Area (acres)",
    "industrial_area_acres": "Industrial Area (acres)",
    "allotted_area_acres": "Allotted Area (acres)",
    "vacant_area_acres": "Vacant Area (acres)",
    "under_construction_area_acres": "Under Construction Area (acres)",
    "under_production_area_acres": "Under Production Area (acres)",
    "boundary_wall_only_area_acres": "Boundary-Wall-Only Area (acres)",
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
    "activity_category": "Activity Classification",
    "recommended_treatment": "Provisional Treatment",
    "hard_gates_display": "Open Validation Gates",
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
    "counterfactual_status": "Counterfactual Status",
    "displacement_risk": "Displacement Risk",
    "fiscal_return_confidence": "Fiscal Return Confidence",
    "fiscal_exposure_status": "Fiscal Exposure Status",
    "legal_status": "Legal Status",
    "compliance_status": "Compliance Status",
    "provisional_treatment": "Provisional Treatment",
    "illustrative_incentive_treatment": "Illustrative Incentive Treatment",
    "illustrative_support_treatment": "Illustrative Incentive Treatment",
    "illustrative_instrument_options": "Illustrative Instrument",
    "illustrative_support_intensity": "Illustrative Support Intensity",
    "fiscal_cap": "Fiscal Cap",
    "sunset": "Sunset",
    "conditions_gates": "Conditions / Gates",
    "open_validation_gates": "Open Validation Gates",
    "main_blockers": "Main Blockers",
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
    "legal_review_required": "Legal classification is not yet validated; D4 legal review required",
    "compliance_non_compliant": "Developer or enterprise compliance concern; sanction / withdrawal review required",
    "compliance_validation_required": "Developer or enterprise compliance requires validation",
    "fiscal_exposure_missing": "Fiscal exposure not yet validated; D5/FBR/customs verification required",
    "high_fiscal_exposure": "High fiscal exposure requires D5/FBR validation",
    "additionality_uncertain": "Additionality is uncertain; activity is not proof incentives caused the activity",
    "counterfactual_not_assessed": "Counterfactual has not been assessed",
    "net_impact_unknown": "Net fiscal/economic impact is not yet validated",
    "incentive_effectiveness_uncertain": "Incentive effectiveness is not yet validated or weak",
    "weak_incentive_effectiveness_evidence": "Vacancy or allotment-only movement is weak evidence of incentive effectiveness",
    "scenario_minimum_confidence_band": "Assumption gate: minimum confidence band not met",
    "scenario_legal_low_risk_required": "Assumption gate: low legal risk required",
    "scenario_fiscal_data_required": "Assumption gate: D5 fiscal data required",
    "scenario_construction_excluded": "Assumption gate: construction-stage zones excluded",
    "scenario_unknown_developer_compliance_blocker": "Assumption gate: developer compliance must be validated",
}


st.set_page_config(
    page_title=APP_CONFIG["title"],
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] {display: none;}
        .block-container {padding-top: 0.65rem; padding-bottom: 2.2rem; max-width: 1320px;}
        h1, h2, h3, h4 {letter-spacing: 0;}
        h3 {font-size: 1.18rem; margin-top: 1.1rem;}
        h4 {font-size: 1rem; margin-top: 0.9rem;}
        .prototype-kicker {
            color: #4b5563;
            font-size: 0.95rem;
            margin-bottom: 0.3rem;
        }
        .mvp-header {
            align-items: flex-start;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            gap: 1rem;
            justify-content: space-between;
            margin-bottom: 0.35rem;
            padding-bottom: 0.45rem;
        }
        .mvp-header-text {max-width: 820px;}
        .mvp-title {
            color: #0f172a;
            font-size: 1.52rem;
            font-weight: 760;
            letter-spacing: 0;
            line-height: 1.12;
            margin-bottom: 0.12rem;
        }
        .mvp-subtitle {
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.35;
            margin-bottom: 0;
        }
        .mvp-header-badges {
            flex: 0 0 auto;
            padding-top: 0.08rem;
            text-align: right;
        }
        .mvp-nav {
            margin: 0.1rem 0 0.95rem 0;
        }
        .answer-box, .mapping-card, .metric-card, .note-card, .output-card, .zone-header-card, .interpretation-card, .case-memo-card, .summary-card, .callout-card, .panel-card {
            border: 1px solid #d8dee9;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.86rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        .metric-card {
            min-height: 92px;
            border-left: 3px solid #2563eb;
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
            font-size: 1.62rem;
            font-weight: 650;
            line-height: 1.15;
            margin-top: 0.28rem;
        }
        .metric-note {
            color: #6b7280;
            font-size: 0.82rem;
            margin-top: 0.25rem;
        }
        .badge-row {display: flex; flex-wrap: wrap; gap: 0.34rem; margin: 0.25rem 0 0.55rem 0;}
        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.2rem 0.52rem;
            font-size: 0.74rem;
            font-weight: 600;
            background: #eef2ff;
            color: #3730a3;
            line-height: 1.15;
            max-width: 100%;
            white-space: normal;
        }
        .badge.warning {background: #fff7ed; color: #9a3412;}
        .badge.good {background: #ecfdf5; color: #047857;}
        .badge.neutral {background: #f3f4f6; color: #374151;}
        .badge.blue {background: #eff6ff; color: #1d4ed8;}
        .badge.red {background: #fef2f2; color: #991b1b;}
        .badge.amber {background: #fffbeb; color: #92400e;}
        .summary-card {
            min-height: 92px;
            margin-bottom: 0.75rem;
        }
        .summary-card-title {
            color: #334155;
            font-size: 0.82rem;
            font-weight: 750;
            line-height: 1.25;
            margin-bottom: 0.35rem;
        }
        .summary-card-value {
            color: #0f172a;
            font-size: 1.35rem;
            font-weight: 760;
            line-height: 1.1;
        }
        .summary-card-note {
            color: #64748b;
            font-size: 0.78rem;
            margin-top: 0.28rem;
        }
        .callout-card {
            background: #f8fafc;
            border-color: #dbe3ef;
            color: #334155;
            line-height: 1.45;
            margin: 0.55rem 0 0.85rem 0;
        }
        .callout-title {
            color: #0f172a;
            font-size: 0.9rem;
            font-weight: 750;
            margin-bottom: 0.25rem;
        }
        .callout-body {
            color: #334155;
            font-size: 0.9rem;
        }
        .panel-card {margin: 0.65rem 0 0.9rem 0;}
        .panel-title {
            color: #0f172a;
            font-size: 0.96rem;
            font-weight: 760;
            margin-bottom: 0.45rem;
        }
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
        .case-memo-card {
            margin-bottom: 0.85rem;
        }
        .case-memo-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 750;
            margin-bottom: 0.45rem;
        }
        .case-memo-body {
            color: #334155;
            font-size: 0.95rem;
            line-height: 1.48;
        }
        .reason-code-row {
            align-items: flex-start;
            display: flex;
            gap: 0.55rem;
            margin: 0.32rem 0;
        }
        .reason-pill {
            background: #eef2ff;
            border: 1px solid #c7d2fe;
            border-radius: 999px;
            color: #3730a3;
            display: inline-block;
            flex: 0 0 auto;
            font-size: 0.76rem;
            font-weight: 750;
            line-height: 1;
            padding: 0.28rem 0.5rem;
        }
        .reason-text {
            color: #334155;
            font-size: 0.92rem;
            line-height: 1.35;
        }
        .case-header-card {
            background: #ffffff;
            border: 1px solid #d8dee9;
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
            margin: 0.55rem 0 0.9rem 0;
            padding: 0.95rem;
        }
        .case-header-title {
            color: #0f172a;
            font-size: 1.25rem;
            font-weight: 780;
            line-height: 1.2;
            margin-bottom: 0.25rem;
        }
        .case-header-meta {
            color: #475569;
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem 0.75rem;
            font-size: 0.88rem;
            margin-bottom: 0.45rem;
        }
        .zone-header-card {
            border-left: 5px solid #2563eb;
            margin: 0.75rem 0 1rem 0;
        }
        .zone-title {
            color: #111827;
            font-size: 1.35rem;
            font-weight: 750;
            line-height: 1.25;
            margin-bottom: 0.35rem;
        }
        .zone-meta {
            color: #475569;
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem 0.7rem;
            font-size: 0.92rem;
        }
        .confidence-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.16rem 0.52rem;
            background: #ecfdf5;
            color: #047857;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .interpretation-card {
            border-left: 5px solid #0f766e;
            margin: 1rem 0;
        }
        .memo-list {
            margin-top: 0.2rem;
            padding-left: 1.2rem;
        }
        div[data-testid="stSelectbox"] label {font-weight: 650;}
        div[data-testid="stRadio"] > label {display: none;}
        div[role="radiogroup"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 999px;
            display: inline-flex;
            gap: 0.16rem;
            padding: 0.16rem;
        }
        div[role="radiogroup"] label {
            background: transparent;
            border-radius: 999px;
            margin: 0;
            padding: 0.14rem 0.34rem;
        }
        div[role="radiogroup"] label:has(input:checked) {
            background: #ffffff;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
        }
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            color: #0f172a;
            font-weight: 650;
        }
        div[data-testid="stButton"] button:hover,
        div[data-testid="stDownloadButton"] button:hover {
            border-color: #64748b;
            color: #0f172a;
        }
        div[data-testid="stDataFrame"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
        }
        @media (max-width: 900px) {
            .mvp-header {display: block;}
            .mvp-header-badges {text-align: left;}
            .mvp-title {font-size: 1.35rem;}
            div[role="radiogroup"] {border-radius: 12px; flex-wrap: wrap;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_demo_outputs(cache_version: str, scenario_items: tuple[tuple[str, object], ...]) -> dict[str, object]:
    _ = cache_version
    return run_pipeline(ROOT, scenario=dict(scenario_items), write_outputs=True)


def apply_posture_defaults() -> None:
    preset = st.session_state.get("policy_posture_preset", "Broad diagnostic screen")
    if preset == "Data confidence conservative":
        preset = "Data-quality conservative"
        st.session_state.policy_posture_preset = preset
    if preset not in POSTURE_DEFAULTS:
        preset = "Broad diagnostic screen"
        st.session_state.policy_posture_preset = preset
    for key, value in POSTURE_DEFAULTS[preset].items():
        st.session_state[key] = value


def initialize_state() -> None:
    legacy_page_map = {
        "Executive View": "Executive Triage",
        "Zone Explorer": "Case Review",
        "Recommendation Engine": "Case Review",
        "Screening Output Engine": "Case Review",
        "Data Intake": "Data Confidence",
        "Data Validation": "Data Confidence",
        "Data Validation & Source Confidence": "Data Confidence",
        "KPI Assurance": "Data Confidence",
        "Export Memo": "Export",
    }
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Executive Triage"
    elif st.session_state.current_page in legacy_page_map:
        st.session_state.current_page = legacy_page_map[st.session_state.current_page]
    elif st.session_state.current_page not in PAGES:
        st.session_state.current_page = "Executive Triage"
    if st.session_state.get("policy_posture_preset") == "Data confidence conservative":
        st.session_state.policy_posture_preset = "Data-quality conservative"
    if "policy_posture_preset" not in st.session_state or st.session_state.policy_posture_preset not in POSTURE_DEFAULTS:
        st.session_state.policy_posture_preset = "Broad diagnostic screen"
        apply_posture_defaults()
    for key, value in POSTURE_DEFAULTS[st.session_state.policy_posture_preset].items():
        st.session_state.setdefault(key, value)
    st.session_state.demo_mode = True
    st.session_state.anonymize_zone_names = True
    st.session_state.setdefault("demo_case_key", "zone_a")
    st.session_state.data_mode = "Synthetic demo data"


def scenario_from_state() -> dict[str, object]:
    return {
        "policy_posture_preset": st.session_state.policy_posture_preset,
        "require_legal_low_risk_for_pilot": bool(st.session_state.require_legal_low_risk_for_pilot),
        "require_fiscal_data_for_pilot": bool(st.session_state.require_fiscal_data_for_pilot),
        "block_high_fiscal_exposure": bool(st.session_state.block_high_fiscal_exposure),
        "include_construction_stage_transition_candidates": bool(
            st.session_state.include_construction_stage_transition_candidates
        ),
        "minimum_data_confidence_band_for_pilot": str(st.session_state.minimum_data_confidence_band_for_pilot),
        "strict_data_confidence_for_all": bool(st.session_state.strict_data_confidence_for_all),
        "treat_unknown_developer_compliance_as_blocker": bool(
            st.session_state.treat_unknown_developer_compliance_as_blocker
        ),
        "prefer_non_fiscal_when_additionality_uncertain": bool(
            st.session_state.prefer_non_fiscal_when_additionality_uncertain
        ),
        "diagnostic_only": bool(st.session_state.diagnostic_only),
    }


def demo_mode_active() -> bool:
    return bool(st.session_state.get("demo_mode", True))


def real_zone_names_visible() -> bool:
    return demo_mode_active() and not bool(st.session_state.get("anonymize_zone_names", True))


def demo_text(value: object, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "<na>"} else default


def _case_pick(
    recommendations: pd.DataFrame,
    mask: pd.Series,
    used_zone_ids: set[str],
    *,
    prefer_low_confidence: bool = False,
    fallback_index: int = 0,
) -> pd.Series:
    candidates = recommendations[mask.fillna(False)].copy()
    fresh = candidates[~candidates["zone_id"].astype(str).isin(used_zone_ids)]
    if not fresh.empty:
        candidates = fresh
    if candidates.empty:
        candidates = recommendations[~recommendations["zone_id"].astype(str).isin(used_zone_ids)].copy()
    if candidates.empty:
        candidates = recommendations.copy()
    if candidates.empty:
        return pd.Series(dtype=object)
    if "data_confidence_score" in candidates.columns:
        candidates = candidates.sort_values("data_confidence_score", ascending=prefer_low_confidence)
    return candidates.iloc[min(fallback_index, len(candidates) - 1)]


def demo_case_catalog(recommendations: pd.DataFrame) -> list[dict[str, object]]:
    if recommendations.empty:
        return []
    activity = recommendations.get("activity_category", pd.Series("", index=recommendations.index)).astype(str)
    band = recommendations.get("data_confidence_band", pd.Series("", index=recommendations.index)).astype(str)
    treatment = recommendations.get("recommended_treatment", pd.Series("", index=recommendations.index)).astype(str)
    gates = recommendations.get("hard_gates_triggered", pd.Series("", index=recommendations.index)).astype(str)
    fiscal_status = recommendations.get("fiscal_exposure_status", pd.Series("", index=recommendations.index)).astype(str)
    legal_status = recommendations.get("legal_status", pd.Series("", index=recommendations.index)).astype(str)

    masks = {
        "zone_a": activity.eq("operating_productive") & band.isin(["high", "medium"]),
        "zone_b": activity.eq("moving_toward_production"),
        "zone_c": band.isin(["low", "do_not_use"]) | treatment.str.contains("More data required", case=False, na=False),
        "zone_d": (
            gates.str.contains("legal|fiscal", case=False, na=False)
            | treatment.str.contains("Legal|Fiscal", case=False, na=False)
            | fiscal_status.str.contains("missing|placeholder", case=False, na=False)
            | legal_status.str.contains("review|required|unknown", case=False, na=False)
        ),
    }

    used: set[str] = set()
    catalog: list[dict[str, object]] = []
    definitions = {case["key"]: case for case in DEMO_CASE_DEFINITIONS}
    for idx, key in enumerate(["zone_a", "zone_b", "zone_c", "zone_d"]):
        row = _case_pick(
            recommendations,
            masks[key],
            used,
            prefer_low_confidence=(key == "zone_c"),
            fallback_index=idx,
        )
        zone_id = demo_text(row.get("zone_id"), f"demo_{key}")
        used.add(str(zone_id))
        definition = definitions[key]
        real_name = demo_text(row.get("zone_name"), "Selected zone")
        anonymous_label = str(definition["anonymous_label"])
        label = f"{anonymous_label} ({real_name})" if real_zone_names_visible() else anonymous_label
        catalog.append(
            {
                "key": key,
                "zone_id": zone_id,
                "real_zone_name": real_name,
                "anonymous_label": anonymous_label,
                "label": label,
                "selector_note": definition["selector_note"],
            }
        )
    return catalog


def demo_cases_by_key(recommendations: pd.DataFrame) -> dict[str, dict[str, object]]:
    return {str(case["key"]): case for case in demo_case_catalog(recommendations)}


def current_demo_case(recommendations: pd.DataFrame) -> dict[str, object] | None:
    cases = demo_cases_by_key(recommendations)
    if not cases:
        return None
    key = str(st.session_state.get("demo_case_key", "zone_a"))
    if key not in cases:
        key = next(iter(cases))
        st.session_state.demo_case_key = key
    return cases[key]


def current_demo_zone_id(recommendations: pd.DataFrame) -> object | None:
    case = current_demo_case(recommendations)
    return case.get("zone_id") if case else None


def anonymized_demo_record(row: pd.Series, case: dict[str, object] | None = None) -> pd.Series:
    out = row.copy()
    if not demo_mode_active() or real_zone_names_visible():
        return out
    label = str(case.get("anonymous_label") if case else "Demo zone")
    out["zone_name"] = label
    if "developer_name" in out.index:
        out["developer_name"] = "Synthetic demo dataset"
    return out


def demo_case_rows(recommendations: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for case in demo_case_catalog(recommendations):
        selected = recommendations[recommendations["zone_id"].astype(str) == str(case["zone_id"])]
        if selected.empty:
            continue
        row = anonymized_demo_record(selected.iloc[0], case)
        row["demo_case_key"] = case["key"]
        row["Demo Case"] = case["label"]
        rows.append(row)
    return pd.DataFrame(rows) if rows else recommendations.head(0).copy()


def demo_display_rows(display_recommendations: pd.DataFrame, recommendations: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for case in demo_case_catalog(recommendations):
        selected = display_recommendations[display_recommendations["zone_id"].astype(str) == str(case["zone_id"])]
        if selected.empty:
            continue
        row = selected.iloc[0].copy()
        if not real_zone_names_visible():
            row["zone_name"] = case["anonymous_label"]
        row["Demo Case"] = case["label"]
        rows.append(row)
    return pd.DataFrame(rows) if rows else display_recommendations.head(0).copy()


def demo_label_maps(recommendations: pd.DataFrame) -> tuple[dict[str, str], dict[str, str]]:
    id_map: dict[str, str] = {}
    name_map: dict[str, str] = {}
    for case in demo_case_catalog(recommendations):
        label = str(case["label"] if real_zone_names_visible() else case["anonymous_label"])
        id_map[str(case["zone_id"])] = label
        name_map[str(case["real_zone_name"])] = label
    return id_map, name_map


def anonymize_demo_table(df: pd.DataFrame, recommendations: pd.DataFrame) -> pd.DataFrame:
    if not demo_mode_active() or real_zone_names_visible() or df.empty:
        return df
    out = df.copy()
    id_map, name_map = demo_label_maps(recommendations)
    if "zone_id" in out.columns:
        for zone_id, label in id_map.items():
            mask = out["zone_id"].astype(str) == zone_id
            for column in ["zone_name", "Zone"]:
                if column in out.columns:
                    out.loc[mask, column] = label
            for column in ["developer_name", "Developer"]:
                if column in out.columns:
                    out.loc[mask, column] = "Synthetic demo dataset"
    for column in ["zone_name", "Zone"]:
        if column in out.columns:
            out[column] = out[column].replace(name_map)
    return out


def demo_scope_table(df: pd.DataFrame, recommendations: pd.DataFrame) -> pd.DataFrame:
    if not demo_mode_active() or df.empty:
        return df
    out = df.copy()
    case_ids = {str(case["zone_id"]) for case in demo_case_catalog(recommendations)}
    case_names = {str(case["real_zone_name"]) for case in demo_case_catalog(recommendations)}
    if "zone_id" in out.columns:
        out = out[out["zone_id"].astype(str).isin(case_ids)]
    elif "Zone" in out.columns:
        out = out[out["Zone"].astype(str).isin(case_names | {"All zones"})]
    return anonymize_demo_table(out, recommendations)


def render_guided_demo_script() -> None:
    with st.expander("Guided demo script", expanded=True):
        for idx, step in enumerate(DEMO_SCRIPT_STEPS, start=1):
            st.write(f"{idx}. {step}")


def render_demo_mode_panel(recommendations: pd.DataFrame) -> None:
    if not demo_mode_active():
        st.caption("Synthetic demo view is not active. Full dataset exploration is enabled.")
        return
    cases = demo_case_catalog(recommendations)
    if not cases:
        st.info("Synthetic demo view is active, but no demo cases are available in the current output set.")
        return
    valid_keys = [str(case["key"]) for case in cases]
    if st.session_state.get("demo_case_key") not in valid_keys:
        st.session_state.demo_case_key = valid_keys[0]
    case_map = {str(case["key"]): case for case in cases}

    with st.container(border=True):
        c1, c2 = st.columns([0.36, 0.64])
        with c1:
            st.selectbox(
                "Demo Cases",
                valid_keys,
                key="demo_case_key",
                format_func=lambda key: str(case_map[key]["label"]),
            )
        with c2:
            selected = case_map[str(st.session_state.demo_case_key)]
            st.markdown(f"**Selected case:** {selected['label']}")
            st.caption("Synthetic demo view shows the four-case walkthrough and hides raw technical logs by default.")
    if real_zone_names_visible():
        st.warning("Do not present real-zone treatment outputs as final. These are screening outputs only.")
    render_guided_demo_script()


def sync_data_mode(summary: dict[str, Any]) -> None:
    if st.session_state.get("data_mode") == "Verified approved data":
        st.session_state.data_mode = "Verified source-cleared data"
    if st.session_state.get("data_mode") not in DATA_MODE_OPTIONS:
        st.session_state.data_mode = "Restricted internal dataset"
    if (summary.get("demo_data_used") or summary.get("demo_data_created")) and st.session_state.data_mode == "Restricted internal dataset":
        st.session_state.data_mode = "Synthetic demo data"


def data_mode_badge_html(mode: str) -> str:
    colors = {
        "Synthetic demo data": ("#ecfdf5", "#047857"),
        "Restricted internal dataset": ("#fff7ed", "#c2410c"),
        "Verified source-cleared data": ("#eff6ff", "#1d4ed8"),
    }
    background, color = colors.get(mode, ("#f8fafc", "#334155"))
    return (
        "<div class='badge-row'>"
        f"<span class='badge' style='background:{background}; color:{color};'>Dataset view: {html.escape(mode)}</span>"
        "</div>"
    )


def render_data_safeguards(summary: dict[str, Any]) -> None:
    st.markdown(data_mode_badge_html(st.session_state.data_mode), unsafe_allow_html=True)
    if st.session_state.data_mode != "Synthetic demo data":
        st.warning(DATA_MODE_WARNING)
        st.caption(SOURCE_PERMISSION_WARNING)
    st.info(PUBLIC_LINK_WARNING)
    st.caption("Raw source text, audit logs, and processing details are hidden from default views.")


def render_header(recommendations: pd.DataFrame, summary: dict[str, Any]) -> str:
    st.markdown(
        "<div class='mvp-header'>"
        "<div class='mvp-header-text'>"
        f"<div class='mvp-title'>{html.escape(APP_CONFIG['title'])}</div>"
        f"<div class='mvp-subtitle'>{html.escape(APP_CONFIG['subtitle'])}</div>"
        "</div>"
        "<div class='mvp-header-badges'>"
        "<div class='badge-row'>"
        f"<span class='badge good'>{html.escape(DATA_PROFILE_LABEL)}</span>"
        f"<span class='badge warning'>{html.escape(HUMAN_REVIEW_LABEL)}</span>"
        "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='mvp-nav'>", unsafe_allow_html=True)
    page = st.radio("View", PAGES, key="current_page", horizontal=True, label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
    return page


def visible_text(value: object, default: str = "Not available") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return default
    replacements = {
        "Placeholder pending D5": "Pending D5 validation",
        "placeholder pending D5": "pending D5 validation",
        "Fiscal exposure placeholder": "Fiscal exposure pending validation",
        "D5 exposure placeholder": "D5 exposure pending validation",
        "D4 placeholder pending": "D4 validation pending",
        "D4 placeholder": "D4 validation status",
        "placeholder-based": "pending validation",
        "Placeholder-based": "Pending validation",
        "placeholder": "pending validation",
        "Placeholder": "Pending validation",
        "Unknown": "Not yet validated",
        "unknown": "not yet validated",
        "Missing": "Not yet validated",
        "missing": "not yet validated",
        "do_not_use": "Do not use for decision",
        "operating_productive": "Operating / productive",
        "moving_toward_production": "Moving toward production",
        "allotted_but_inactive": "Allotment-only / not yet productive",
        "vacant_or_speculative": "Idle / weak activity evidence",
        '"nan" value in visible field': "Not available value in visible field",
        "MVP": "prototype",
        "debug": "technical",
        "Debug": "Technical",
        "eligible": "potential review flag / subject to validation",
        "Eligible": "Potential review flag / subject to validation",
        "approved": "source-cleared",
        "Approved": "Source-cleared",
        "approval": "clearance",
        "Approval": "Clearance",
        "data-quality issue": "validation flag",
        "Data-quality issue": "Validation flag",
        "data-quality issues": "validation flags",
        "Data-quality issues": "Validation flags",
        "contradiction": "cross-source/status conflict",
        "Contradiction": "Cross-source/status conflict",
        "contradictions": "cross-source/status conflicts",
        "Contradictions": "Cross-source/status conflicts",
        "normalized data": "structured screening dataset",
        "Normalized data": "Structured screening dataset",
        "model decides": "framework indicates",
        "Model decides": "Framework indicates",
        "policy recommendation": "policy screening output",
        "Policy recommendation": "Policy screening output",
        "recommendations": "screening outputs",
        "Recommendations": "Screening outputs",
        "recommendation": "screening output",
        "Recommendation": "Screening output",
        "fiscal estimate": "fiscal analysis output",
        "incentive approval": "incentive clearance",
    }
    output = text
    for old, new in replacements.items():
        output = output.replace(old, new)
    output = re.sub(r"(?<![A-Za-z])nan(?![A-Za-z])", "Not available", output, flags=re.IGNORECASE)
    return output


def metric_card(label: str, value: object, note: str = "") -> None:
    st.markdown(
        "<div class='metric-card'>"
        f"<div class='metric-label'>{html.escape(visible_text(label))}</div>"
        f"<div class='metric-value'>{html.escape(visible_text(value))}</div>"
        f"<div class='metric-note'>{html.escape(visible_text(note, ''))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def callout_card(title: str, body: str) -> None:
    st.markdown(
        "<div class='callout-card'>"
        f"<div class='callout-title'>{html.escape(visible_text(title))}</div>"
        f"<div class='callout-body'>{html.escape(visible_text(body))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def summary_card(title: str, value: object, note: str = "") -> None:
    st.markdown(
        "<div class='summary-card'>"
        f"<div class='summary-card-title'>{html.escape(visible_text(title))}</div>"
        f"<div class='summary-card-value'>{html.escape(visible_text(value))}</div>"
        f"<div class='summary-card-note'>{html.escape(visible_text(note, ''))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def badge_html(text: object, tone: str = "neutral") -> str:
    safe_tone = tone if tone in {"neutral", "good", "warning", "blue", "red", "amber"} else "neutral"
    return f"<span class='badge {safe_tone}'>{html.escape(visible_text(text))}</span>"


def confidence_tone(value: object) -> str:
    text = str(value or "").lower()
    if "high" in text:
        return "good"
    if "medium" in text:
        return "blue"
    if "low" in text:
        return "amber"
    if "do not use" in text or "do_not_use" in text:
        return "red"
    return "neutral"


def pathway_tone(value: object) -> str:
    text = str(value or "").lower()
    if "pilot" in text:
        return "blue"
    if "more data" in text or "do not use" in text:
        return "amber"
    if "legal" in text or "fiscal" in text or "fbr" in text:
        return "warning"
    if "no new" in text or "phase-out" in text or "sanction" in text:
        return "red"
    return "neutral"


def note_card(title: str, lines: list[str]) -> None:
    body = "".join(f"<li>{html.escape(visible_text(line))}</li>" for line in lines)
    st.markdown(
        "<div class='note-card'>"
        f"<strong>{html.escape(visible_text(title))}</strong>"
        f"<ul>{body}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )


def mapping_card(title: str, items: list[str]) -> None:
    body = "".join(f"<li>{html.escape(visible_text(item))}</li>" for item in items)
    st.markdown(
        "<div class='mapping-card'>"
        f"<strong>{html.escape(visible_text(title))}</strong>"
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
    return "; ".join(visible_text(GATE_LABELS.get(part, part.replace("_", " ").title())) for part in parts)


def display_reason_text(text: str) -> str:
    replacements = {
        "Possible pilot screen candidate": "Potential pilot-review flag subject to validation",
        "No final fiscal support can be recommended": "Temporary transition support cannot be recommended",
        "Fiscal exposure missing": "Fiscal exposure pending validation",
        "D5/FBR/customs verification required": "D5/FBR/customs verification required",
    }
    output = str(text)
    for old, new in replacements.items():
        output = output.replace(old, new)
    return visible_text(output)


def decode_reason_codes(codes: object, reason_codes: dict[str, str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Reason Code": code, "Reason": display_reason_text(reason_codes.get(code, "Unmapped reason code"))}
            for code in split_reason_codes(codes)
        ]
    )


def activity_label(value: object) -> str:
    labels = {
        "operating_productive": "Operating / productive",
        "moving_toward_production": "Moving toward production",
        "allotted_but_inactive": "Allotment-only / not yet productive",
        "vacant_or_speculative": "Idle / weak activity evidence",
        "unclear": "Requires verification",
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
        return f"D4 validation status: {value}"
    return "D4 validation pending"


def fiscal_label(value: object) -> str:
    value = str(value or "unknown").lower()
    if value == "unknown":
        return "D5 exposure pending validation"
    return f"D5 exposure: {value}"


def readable_status(value: object, default: str = "Requires validation") -> str:
    text = str(value or "").strip()
    if not text or text.lower() in {"nan", "none", "unknown", "missing"}:
        return default
    return text.replace("_", " ").title()


def treatment_label(text: object) -> str:
    output = str(text or "")
    if output == "More data required":
        return "More data required before fiscal/calibration use"
    replacements = {
        "Possible pilot screen candidate pending D4 legal review and D5 fiscal verification": (
            "Potential pilot-review flag subject to D4/D5 validation"
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
    output = visible_text(output)
    if "subject to validation" not in output.lower() and "provisional" not in output.lower():
        output = f"{output} - provisional, subject to validation"
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
    return visible_text(output)


def display_memo_text(text: object) -> str:
    output = str(text or "")
    replacements = {
        "possible pilot screen candidate": "potential pilot-review candidate subject to validation",
        "pilot screen": "pilot-review screen",
    }
    for old, new in replacements.items():
        output = output.replace(old, new)
    output = visible_text(output)
    if "human review" not in output.lower():
        output = f"{output} Human review required."
    return output


def split_pipe_text(text: object) -> list[str]:
    return [part.strip() for part in str(text or "").split("|") if part.strip()]


def render_bullets(items: list[str]) -> None:
    if not items:
        st.write("None identified by the prototype.")
        return
    st.markdown(
        "<ul class='memo-list'>" + "".join(f"<li>{html.escape(visible_text(item))}</li>" for item in items) + "</ul>",
        unsafe_allow_html=True,
    )


def output_card(label: str, value: object) -> None:
    st.markdown(
        "<div class='output-card'>"
        f"<div class='output-label'>{html.escape(visible_text(label))}</div>"
        f"<div class='output-value'>{html.escape(visible_text(value))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def compact_text(value: object, max_chars: int = 150) -> str:
    text = visible_text(value)
    parts = split_pipe_text(text)
    if parts:
        text = visible_text(parts[0])
        if len(parts) > 1:
            text = f"{text} (+{len(parts) - 1} more)"
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "..."
    return text


def display_value(value: object, default: str = "Not available") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "<na>"}:
        return default
    return visible_text(text, default)


def format_area(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Not available"
    if pd.isna(number):
        return "Not available"
    if number.is_integer():
        return f"{int(number):,} acres"
    return f"{number:,.2f} acres"


def source_reference(row: pd.Series) -> str:
    package = DATASET_BASIS_LABEL
    source_row = display_value(row.get("source_row"), "")
    if source_row:
        return f"{package} / row {source_row}"
    return package


def combined_idle_area(row: pd.Series) -> str:
    parts = []
    for label, field in [
        ("Vacant", "vacant_area_acres"),
        ("Boundary-wall-only", "boundary_wall_only_area_acres"),
        ("Unsold", "unsold_area_acres"),
    ]:
        value = format_area(row.get(field))
        if value != "Not available":
            parts.append(f"{label}: {value}")
    return "; ".join(parts) if parts else "Not available"


def selected_zone_summary(row: pd.Series) -> pd.DataFrame:
    rows = [
        ("Zone ID", row.get("zone_id")),
        ("Zone", row.get("zone_name")),
        ("Province", row.get("province")),
        ("Developer", row.get("developer_name")),
        ("Zone type", row.get("zone_type")),
        ("Reported operational status", row.get("operational_status")),
        ("Activity classification", row.get("Activity Classification", row.get("Reported Activity"))),
        ("Industrial area", format_area(row.get("industrial_area_acres"))),
        ("Allotted area", format_area(row.get("allotted_area_acres"))),
        ("Under construction area", format_area(row.get("under_construction_area_acres"))),
        ("Under production area", format_area(row.get("under_production_area_acres"))),
        ("Vacant / idle area", combined_idle_area(row)),
        ("Data confidence", row.get("Data Confidence")),
        ("Legal status", row.get("Legal Status")),
        ("Fiscal status", row.get("Fiscal Status")),
        ("Compliance status", row.get("compliance_status")),
        ("Additionality confidence", row.get("additionality_confidence")),
        ("Net fiscal/economic impact", row.get("net_fiscal_economic_impact")),
        ("Incentive-effectiveness confidence", row.get("incentive_effectiveness_confidence")),
        ("Structured dataset / source row", source_reference(row)),
    ]
    return pd.DataFrame(
        [{"Field": field, "Value": display_value(value)} for field, value in rows],
        columns=["Field", "Value"],
    )


def selected_zone_interpretation(row: pd.Series) -> pd.DataFrame:
    activity = str(row.get("activity_category") or "").strip()
    activity_text = {
        "operating_productive": (
            "Reported data indicates production activity. This is evidence of activity, not proof that incentives caused it."
        ),
        "moving_toward_production": (
            "Reported data indicates construction-stage movement. The zone is not treated as operating/productive."
        ),
        "allotted_but_inactive": (
            "Reported data indicates allotment movement without production or construction evidence."
        ),
        "vacant_or_speculative": (
            "Reported data indicates idle, vacant, unsold, or boundary-wall-only signals with weak activity evidence."
        ),
        "unclear": "Current data does not support a verified activity classification.",
    }.get(activity, "Current data requires verification before interpretation.")

    blockers = split_pipe_text(row.get("main_blockers", ""))
    gaps = "; ".join(blockers[:4]) if blockers else "Source-row, enterprise-level, legal, fiscal, and additionality checks remain open."
    treatment = display_value(row.get("Provisional Treatment", row.get("provisional_treatment")))
    next_action = display_action_text(row.get("next_actions", "Human review required."))
    rows = [
        ("What appears to be happening", activity_text),
        (
            "What cannot yet be concluded",
            "The app does not infer incentive causation, net positive fiscal/economic impact, legal clearance, or fiscal affordability from reported activity.",
        ),
        ("What data is missing", gaps),
        (
            "How this zone might fit fiscal/calibration/pilot review",
            f"Current screen: {treatment}. Use this as an input to D4 legal review, D5 fiscal validation, D6 calibration assumptions, and D7 pilot-review design.",
        ),
        ("Next action", next_action),
    ]
    return pd.DataFrame([{"Question": visible_text(key), "Interpretation": visible_text(value)} for key, value in rows])


def calibration_treatment_class(row: pd.Series) -> str:
    treatment = display_value(
        row.get("illustrative_support_treatment", row.get("illustrative_incentive_treatment")),
        "More data required before treatment",
    )
    if treatment == "Temporary grandfathering / transition review":
        treatment = "Legal/transition review"
    legal_risk = str(row.get("legal_risk_level", "")).strip().lower()
    if treatment == "Limited cost-based support review" and legal_risk in {"", "unknown", "high"}:
        return "Legal/transition review"
    allowed = {
        "No new fiscal support",
        "Non-fiscal support only",
        "Legal/transition review",
        "Limited cost-based support review",
        "Pilot-only cost-based support review",
        "Phase-out / sanction review",
        "More data required before treatment",
    }
    return treatment if treatment in allowed else "More data required before treatment"


def calibration_possible_instrument(row: pd.Series, treatment_class: str) -> str:
    activity = str(row.get("activity_category", "")).strip()
    raw = display_value(row.get("illustrative_instrument_options"), "None")
    replacements = {
        "CAPEX expensing review": "Immediate expensing / CAPEX deduction review",
        "Administrative / facilitation support only": "Administrative facilitation / one-window support",
    }
    for old, new in replacements.items():
        raw = raw.replace(old, new)
    if activity == "vacant_or_speculative" or treatment_class in {
        "No new fiscal support",
        "Phase-out / sanction review",
        "More data required before treatment",
    }:
        return "None"
    allowed = [
        "None",
        "Immediate expensing / CAPEX deduction review",
        "Training deduction review",
        "R&D deduction review",
        "Infrastructure-linked non-fiscal support",
        "Administrative facilitation / one-window support",
        "To be determined after D5/D6 validation",
    ]
    for option in allowed:
        if option in raw:
            return option
    if treatment_class == "Non-fiscal support only":
        return "Administrative facilitation / one-window support"
    return "To be determined after D5/D6 validation"


def calibration_support_intensity(row: pd.Series, treatment_class: str) -> str:
    additionality = str(row.get("additionality_confidence", "Unknown")).strip().lower()
    raw = display_value(row.get("illustrative_support_intensity"), "Not determined")
    if treatment_class in {"No new fiscal support", "Phase-out / sanction review", "More data required before treatment"}:
        return "None"
    if additionality in {"", "unknown"} and raw == "High":
        return "Not determined"
    return raw if raw in {"None", "Low", "Medium", "High", "Not determined"} else "Not determined"


def calibration_fiscal_cap(row: pd.Series, treatment_class: str) -> str:
    fiscal_status = str(row.get("fiscal_exposure_status", "")).strip().lower()
    fiscal_level = str(row.get("fiscal_exposure_level", "")).strip().lower()
    gates = str(row.get("hard_gates_triggered", ""))
    if fiscal_status in {"", "missing", "placeholder"} or fiscal_level in {"", "unknown", "missing"} or "fiscal_exposure_missing" in gates:
        return "Pending D5 validation"
    raw = display_value(row.get("fiscal_cap"), "")
    if raw in {"Pending D5 validation", "No cap set", "Cap required before policy use", "Not applicable"}:
        return raw
    if treatment_class in {"Limited cost-based support review", "Pilot-only cost-based support review", "Legal/transition review"}:
        return "Cap required before policy use"
    if treatment_class in {"No new fiscal support", "Non-fiscal support only", "Phase-out / sanction review", "More data required before treatment"}:
        return "Not applicable"
    return "No cap set"


def calibration_duration(row: pd.Series, treatment_class: str) -> str:
    raw = display_value(row.get("sunset"), "")
    if raw in {
        "Not applicable",
        "Temporary only",
        "Pilot period only",
        "No later than 30 June 2035, subject to legal commitments",
    }:
        return raw
    if treatment_class == "Pilot-only cost-based support review":
        return "Pilot period only"
    if treatment_class in {"Limited cost-based support review", "Legal/transition review"}:
        return "No later than 30 June 2035, subject to legal commitments"
    return "Not applicable"


def calibration_conditions(row: pd.Series, treatment_class: str) -> str:
    conditions = [
        "D4 legal review",
        "D5/FBR fiscal exposure validation",
        "developer/enterprise compliance validation",
        "additionality validation",
        "KPI assurance",
        "audit trigger",
        "enterprise-level data",
    ]
    if treatment_class in {"Limited cost-based support review", "Pilot-only cost-based support review", "Legal/transition review"}:
        conditions.append("Finance Division / Tax Policy review")
    return "; ".join(dict.fromkeys(conditions))


def calibration_why(row: pd.Series, treatment_class: str, instrument: str, cap: str) -> str:
    zone = display_value(row.get("zone_name"), "This zone")
    activity = activity_label(row.get("activity_category")).lower()
    confidence = display_value(row.get("Data Confidence", row.get("data_confidence_band")), "unknown")
    additionality = display_value(row.get("additionality_confidence"), "Unknown")
    return (
        f"{zone} is shown as {treatment_class} because the current screen indicates {activity} and data confidence is "
        f"{confidence}. The possible instrument is {instrument}, with fiscal cap status shown as {cap}. "
        f"Additionality confidence is {additionality}, so the output remains a D6 calibration input only and cannot be "
        "read as a policy decision, fiscal analysis output, tax decision, or incentive clearance."
    )


def calibration_output_table(row: pd.Series) -> pd.DataFrame:
    treatment_class = calibration_treatment_class(row)
    instrument = calibration_possible_instrument(row, treatment_class)
    intensity = calibration_support_intensity(row, treatment_class)
    cap = calibration_fiscal_cap(row, treatment_class)
    duration = calibration_duration(row, treatment_class)
    conditions = calibration_conditions(row, treatment_class)
    why = calibration_why(row, treatment_class, instrument, cap)
    return pd.DataFrame(
        [
            {"Field": "Treatment class", "Value": visible_text(treatment_class)},
            {"Field": "Possible instrument", "Value": visible_text(instrument)},
            {"Field": "Support intensity", "Value": visible_text(intensity)},
            {"Field": "Fiscal cap", "Value": visible_text(cap)},
            {"Field": "Duration / sunset", "Value": visible_text(duration)},
            {"Field": "Conditions", "Value": visible_text(conditions)},
            {"Field": "Why this treatment", "Value": visible_text(why)},
        ],
        columns=["Field", "Value"],
    )


def render_calibration_output(row: pd.Series) -> None:
    st.markdown("### Calibration Output &mdash; Illustrative Only", unsafe_allow_html=True)
    st.warning(
        "Illustrative only - for logic demonstration. Not a policy decision, fiscal analysis output, tax decision, "
        "or incentive clearance. Any cost-based support shown here is temporary transition support only; all SEZ fiscal "
        "incentives phase out by 30 June 2035."
    )
    st.dataframe(calibration_output_table(row), width="stretch", hide_index=True)


def render_zone_header(row: pd.Series) -> None:
    confidence = display_value(row.get("Data Confidence"))
    st.markdown(
        "<div class='zone-header-card'>"
        f"<div class='zone-title'>{html.escape(display_value(row.get('zone_name'), 'Selected zone'))}</div>"
        "<div class='zone-meta'>"
        f"<span><strong>Province:</strong> {html.escape(display_value(row.get('province')))}</span>"
        f"<span><strong>Developer:</strong> {html.escape(display_value(row.get('developer_name')))}</span>"
        f"<span><strong>Reported status:</strong> {html.escape(display_value(row.get('operational_status')))}</span>"
        f"<span><strong>Data confidence:</strong> <span class='confidence-badge'>{html.escape(confidence)}</span></span>"
        "</div>"
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
    if "open_validation_gates" in view.columns:
        view["Open Gates"] = view["open_validation_gates"].fillna("").astype(str).replace("", "None identified")
    else:
        view["Open Gates"] = view["hard_gates_display"]
    view["Reported Activity"] = view["activity_category"].apply(activity_label)
    view["Activity Classification"] = view["Reported Activity"]
    view["Data Confidence"] = view.apply(confidence_label, axis=1)
    view["Legal Status"] = view["legal_status"] if "legal_status" in view.columns else view["legal_risk_level"].apply(legal_label)
    view["Fiscal Status"] = (
        view["fiscal_exposure_status"] if "fiscal_exposure_status" in view.columns else view["fiscal_exposure_level"].apply(fiscal_label)
    )
    view["Additionality Status"] = (
        view["additionality_confidence"].apply(readable_status)
        if "additionality_confidence" in view.columns
        else pd.Series(["Requires validation"] * len(view), index=view.index)
    )
    view["Provisional Treatment"] = view["recommended_treatment"].apply(treatment_label)
    view["Main Reason Codes"] = view["reason_codes"].apply(main_reason_codes)
    view["Next Action"] = view["next_actions"].apply(next_action_label)
    for column in view.columns:
        if pd.api.types.is_object_dtype(view[column]) or pd.api.types.is_string_dtype(view[column]):
            view[column] = view[column].apply(lambda value: visible_text(value, "Not available"))
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


def count_text_matches(frame: pd.DataFrame, columns: list[str], pattern: str) -> int:
    blank = pd.Series([""] * len(frame), index=frame.index)
    text = blank.copy()
    for column in columns:
        text = text + " " + frame.get(column, blank).fillna("").astype(str)
    return int(text.str.contains(pattern, case=False, regex=True).sum())


def legal_review_count(recommendations: pd.DataFrame) -> int:
    return count_text_matches(
        recommendations,
        ["required_legal_action", "hard_gates_triggered", "reason_codes", "next_actions"],
        "legal|d4|r01|r02",
    )


def fiscal_validation_count(recommendations: pd.DataFrame) -> int:
    return count_text_matches(
        recommendations,
        ["required_fbr_action", "hard_gates_triggered", "reason_codes", "next_actions"],
        "fbr|customs|fiscal|d5|r09",
    )


def support_review_flag_count(display_recommendations: pd.DataFrame) -> int:
    return count_text_matches(
        display_recommendations,
        ["Provisional Treatment", "Next Action", "Main Reason Codes"],
        "support|transition|pilot|facilitation|cost-based",
    )


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
                "Current Status": "Pending D5 and FBR validation",
                "Why It Matters": "Needed to estimate fiscal exposure and avoid treating activity as proof of incentive effectiveness.",
                "Owner / Validator": "FBR / Finance",
            },
            {
                "Data Category": "Legal data",
                "Required Fields": "Development agreements; enterprise certificates; sunset clauses; change-in-law, arbitration, and compensation clauses",
                "Current Status": "Pending D4 legal review",
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


def validation_source_reference(source_file: object, source_row: object) -> str:
    row_text = display_value(source_row, "")
    if row_text:
        return f"{DATASET_BASIS_LABEL} / row {row_text}"
    return DATASET_BASIS_LABEL


def validation_owner(field: object, issue_type: object, description: object) -> str:
    text = f"{field} {issue_type} {description}".lower()
    if any(token in text for token in ["legal", "contract", "sunset", "grandfather"]):
        return "Legal team / BOI / SEZA"
    if any(token in text for token in ["fiscal", "fbr", "customs", "tax"]):
        return "FBR / Finance Division"
    if any(token in text for token in ["enterprise", "plot-level", "allottee"]):
        return "BOI / SEZA / developers / enterprises"
    if any(token in text for token in ["status", "production", "construction", "vacant", "boundary"]):
        return "BOI / SEZA source owner"
    if any(token in text for token in ["area", "acre", "industrial", "allotted", "unsold"]):
        return "BOI / SEZA data team"
    if any(token in text for token in ["coverage", "definition", "universe", "source-row", "source row", "original workbook"]):
        return "BOI / REMIT / consultant team"
    if any(token in text for token in ["duplicate", "alias", "zone name"]):
        return "BOI / SEZA registry owner"
    return "BOI / SEZA data team"


def validation_flag_name(row: pd.Series) -> str:
    field = str(row.get("field_name", "") or "").lower()
    issue_type = str(row.get("issue_type", "") or "").lower()
    description = str(row.get("issue_description", "") or "").lower()
    text = f"{field} {issue_type} {description}"
    if "legal" in text:
        return "Missing legal data"
    if any(token in text for token in ["fiscal", "fbr", "customs", "tax"]):
        return "Missing fiscal data"
    if any(token in text for token in ["enterprise", "plot-level", "allottee"]):
        return "Missing enterprise-level data"
    if "duplicate" in text or "highly similar" in text or "alias" in text:
        return "Possible duplicate zone record"
    if "zone name" in text and ("conflict" in text or "similar" in text):
        return "Conflicting zone names"
    if "under construction" in text and "production" in text:
        return "Under-construction vs under-production mismatch"
    if "operational_status/under_production_area_acres" in field:
        return "Status mismatch"
    if any(token in text for token in ["exceeds", "differs", "reconcile", "area_total", "allotted + unsold"]):
        return "Acreage totals do not reconcile"
    if any(token in text for token in ["source_scope", "coverage", "definition", "universe"]):
        return "Coverage / definition issue"
    if any(token in text for token in ["source-row", "source row", "original workbook", "source digest"]):
        return "Source-row verification required"
    if "nan" in text:
        return "Not available value in visible field"
    if issue_type == "missing":
        return "Missing field"
    if issue_type == "contradiction":
        return "Cross-source/status conflict"
    return display_value(row.get("issue_description"), "Validation flag")


def validation_row(
    *,
    zone: object,
    field: object,
    flag: object,
    severity: object,
    why: object,
    fix: object,
    source: object,
    owner: object,
) -> dict[str, object]:
    return {
        "Zone": display_value(zone, "All zones"),
        "Field": readable_field(str(field or "")) if str(field or "").strip() else "Screening dataset",
        "Validation flag": display_value(flag, "Validation flag"),
        "Severity": display_value(severity, "Caution"),
        "Why it matters": display_value(why, "This field affects screening confidence and decision routing."),
        "Recommended fix": display_value(fix, "Manual source review required."),
        "Source file / sheet / row": display_value(source, DATASET_BASIS_LABEL),
        "Owner": display_value(owner, "BOI / SEZA data team"),
    }


def supplemental_validation_rows(frames: dict[str, pd.DataFrame]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    recommendations = frames.get("recommendations", pd.DataFrame())
    zones = frames.get("zones", pd.DataFrame())

    for _, rec in recommendations.iterrows():
        source = validation_source_reference(rec.get("source_file"), rec.get("source_row"))
        if str(rec.get("legal_status", "")).lower() in {"requires d4 review", "high risk"} or "Legal status not validated" in str(
            rec.get("main_blockers", "")
        ):
            rows.append(
                validation_row(
                    zone=rec.get("zone_name"),
                    field="legal classification / contractual status",
                    flag="Missing legal data",
                    severity="Material",
                    why="D4 legal and contractual status must be validated before treatment, phase-out, grandfathering, or pilot use.",
                    fix="Replace pending legal fields with reviewed D4 legal classification, contractual constraints, and sunset/grandfathering assessment.",
                    source=source,
                    owner="Legal team / BOI / SEZA",
                )
            )
        if str(rec.get("fiscal_exposure_status", "")).lower() in {"missing", "placeholder"} or "Fiscal exposure missing" in str(
            rec.get("main_blockers", "")
        ):
            rows.append(
                validation_row(
                    zone=rec.get("zone_name"),
                    field="fiscal exposure / FBR / customs",
                    flag="Missing fiscal data",
                    severity="Material",
                    why="D5/FBR/customs data are required before fiscal cost, cap, calibration, or temporary transition-support review.",
                    fix="Load validated CIT, customs exemption, tax-paid, and incentive-utilization data by zone and enterprise.",
                    source=source,
                    owner="FBR / Finance Division",
                )
            )
        if "Enterprise-level evidence missing" in str(rec.get("main_blockers", "")):
            rows.append(
                validation_row(
                    zone=rec.get("zone_name"),
                    field="enterprise / plot-level evidence",
                    flag="Missing enterprise-level data",
                    severity="Material",
                    why="Enterprise and plot-level evidence is needed to verify activity, additionality, compliance, and KPI readiness.",
                    fix="Map enterprise certificates, plot status, production dates, employment, exports, investment, and verification evidence to the zone record.",
                    source=source,
                    owner="BOI / SEZA / developers / enterprises",
                )
            )
        if "R19" in str(rec.get("reason_codes", "")):
            rows.append(
                validation_row(
                    zone=rec.get("zone_name"),
                    field="source row",
                    flag="Source-row verification required",
                    severity="Caution",
                    why="Exact row-level verification is required before using the structured screening dataset for policy use.",
                    fix="Verify this record against the original workbook and source documents, then update source lineage notes.",
                    source=source,
                    owner="BOI / REMIT / consultant team",
                )
            )

    for _, zone in zones.iterrows():
        for column in zones.columns:
            value = zone.get(column)
            if isinstance(value, str) and value.strip().lower() == "nan":
                rows.append(
                    validation_row(
                        zone=zone.get("zone_name"),
                        field=column,
                        flag="Not available value in visible field",
                        severity="Caution",
                        why="Visible unavailable-value strings can be misread as real data and weaken client-facing confidence.",
                        fix="Replace unavailable-value strings with blank, not-yet-validated, or source-verified values.",
                        source=validation_source_reference(zone.get("source_file"), zone.get("source_row")),
                        owner="BOI / SEZA data team",
                    )
                )
    return rows


def validation_display_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = []
    if "issues" in frames and not frames["issues"].empty:
        parts.append(frames["issues"].assign(flag_group="Validation flag"))
    if "contradictions" in frames and not frames["contradictions"].empty:
        parts.append(frames["contradictions"].assign(flag_group="Cross-source/status conflict"))
    rows: list[dict[str, object]] = []
    if parts:
        combined = pd.concat(parts, ignore_index=True, sort=False)
        for _, row in combined.iterrows():
            rows.append(
                validation_row(
                    zone=row.get("zone_name", "All zones"),
                    field=row.get("field_name", ""),
                    flag=validation_flag_name(row),
                    severity=severity_label(row.get("severity")),
                    why=row.get("model_impact", ""),
                    fix=row.get("recommended_fix", "Manual source review required."),
                    source=validation_source_reference(row.get("source_file"), row.get("source_row")),
                    owner=validation_owner(row.get("field_name"), row.get("issue_type"), row.get("issue_description")),
                )
            )
    rows.extend(supplemental_validation_rows(frames))
    return pd.DataFrame(
        rows,
        columns=[
            "Zone",
            "Field",
            "Validation flag",
            "Severity",
            "Why it matters",
            "Recommended fix",
            "Source file / sheet / row",
            "Owner",
        ],
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
    for column in out.columns:
        if pd.api.types.is_object_dtype(out[column]) or pd.api.types.is_string_dtype(out[column]):
            out[column] = out[column].apply(lambda value: visible_text(value, "Not available"))
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
        "zone_name",
        "province",
        "Activity Classification",
        "Data Confidence",
        "Legal Status",
        "Fiscal Status",
        "Additionality Status",
        "Provisional Treatment",
        "Open Gates",
        "Main Reason Codes",
        "Next Action",
    ]
    return display_recommendations[columns].rename(
        columns={
            "zone_name": "Zone",
            "province": "Province",
            "Activity Classification": "Activity classification",
            "Data Confidence": "Data confidence",
            "Legal Status": "Legal status",
            "Fiscal Status": "Fiscal status",
            "Additionality Status": "Additionality status",
            "Provisional Treatment": "Review pathway",
            "Open Gates": "Open gates",
            "Main Reason Codes": "Main reason codes",
            "Next Action": "Next action",
        }
    )


EXECUTIVE_FILTER_OPTIONS = [
    "All",
    "More data required",
    "Legal review required",
    "Fiscal/FBR verification required",
    "Transition review",
    "Potential pilot-review flag",
    "Low confidence",
]


def executive_pathway_text(row: pd.Series) -> str:
    raw = row.get("provisional_treatment", row.get("recommended_treatment", row.get("Provisional Treatment", "")))
    text = display_value(raw, "Human review required")
    replacements = {
        "Possible pilot screen candidate pending D4 legal review and D5 fiscal verification": (
            "Potential pilot-review flag subject to D4/D5 validation"
        ),
        "Potential pilot-review flag - subject to D4/D5 validation": (
            "Potential pilot-review flag subject to D4/D5 validation"
        ),
        "Possible transition candidate": "Transition review",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if "Potential pilot-review flag" in text and "D4/D5 validation" not in text:
        text = f"{text} subject to D4/D5 validation"
    return visible_text(text)


def executive_open_gates(row: pd.Series) -> str:
    gates = split_pipe_text(row.get("open_validation_gates", ""))
    if not gates:
        gates = split_pipe_text(row.get("blocking_validation_requirements", ""))
    if not gates:
        formatted = format_gates(row.get("hard_gates_triggered", ""))
        gates = [] if formatted == "None" else [formatted]
    if not gates:
        return "None identified"
    return "; ".join(visible_text(gate) for gate in gates)


def executive_triage_table(recommendations: pd.DataFrame) -> pd.DataFrame:
    table = pd.DataFrame(
        {
            "Zone": recommendations.get("zone_name", pd.Series(dtype=str)).apply(display_value),
            "Province": recommendations.get("province", pd.Series(dtype=str)).apply(display_value),
            "Activity category": recommendations.get("activity_category", pd.Series(dtype=str)).apply(activity_label),
            "Data confidence": recommendations.get("data_confidence_band", pd.Series(dtype=str)).apply(
                lambda value: visible_text(str(value).replace("_", " ").title(), "Not available")
            ),
            "Review pathway": recommendations.apply(executive_pathway_text, axis=1),
            "Reason codes": recommendations.get("reason_codes", pd.Series(dtype=str)).apply(main_reason_codes),
            "Open gates": recommendations.apply(executive_open_gates, axis=1),
            "Validator / owner": recommendations.get("validator_owner", pd.Series(dtype=str)).apply(display_value),
            "Next action": recommendations.get("next_actions", pd.Series(dtype=str)).apply(next_action_label),
        }
    )
    for column in table.columns:
        table[column] = table[column].apply(display_value)
    return table


def executive_count(table: pd.DataFrame, pattern: str) -> int:
    text = table.astype(str).agg(" ".join, axis=1)
    return int(text.str.contains(pattern, case=False, regex=True, na=False).sum())


def executive_pathway_summary(table: pd.DataFrame) -> pd.DataFrame:
    counts = table["Review pathway"].value_counts(dropna=False).reset_index()
    counts.columns = ["Review pathway", "Zones"]
    total = max(int(counts["Zones"].sum()), 1)
    counts["Share"] = counts["Zones"].apply(lambda count: f"{count / total:.0%}")
    return counts


def executive_value_counts(
    recommendations: pd.DataFrame,
    column: str,
    *,
    split_pipe: bool = False,
    limit: int = 8,
) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    if column not in recommendations.columns:
        return pd.DataFrame(columns=["Signal", "Zones"])
    for value in recommendations[column].fillna("").astype(str):
        parts = split_pipe_text(value) if split_pipe else split_reason_codes(value)
        for part in parts:
            clean = visible_text(part)
            if clean.lower() in {"none", "none identified", "not available"}:
                continue
            counter[clean] += 1
    rows = [{"Signal": key, "Zones": count} for key, count in counter.most_common(limit)]
    return pd.DataFrame(rows, columns=["Signal", "Zones"])


def render_pathway_summary_cards(summary: pd.DataFrame) -> None:
    if summary.empty:
        callout_card("Pathway summary", "No review pathways were generated by the current run.")
        return
    for start in range(0, len(summary), 3):
        cols = st.columns(3)
        for col, (_, row) in zip(cols, summary.iloc[start : start + 3].iterrows()):
            with col:
                summary_card(row.get("Review pathway"), row.get("Zones"), f"{row.get('Share')} of screened zones")


def executive_filter_mask(table: pd.DataFrame, selected_filter: str) -> pd.Series:
    if selected_filter == "All":
        return pd.Series([True] * len(table), index=table.index)
    text = table.astype(str).agg(" ".join, axis=1)
    patterns = {
        "More data required": "More data required",
        "Legal review required": "legal|D4|R01|R02|R14|R20",
        "Fiscal/FBR verification required": "fiscal|FBR|customs|D5|R09|R10|R13|R24",
        "Transition review": "transition|grandfather",
        "Potential pilot-review flag": "Potential pilot-review flag",
        "Low confidence": "Low|Do not use",
    }
    return text.str.contains(patterns.get(selected_filter, ""), case=False, regex=True, na=False)


def render_footer() -> None:
    st.markdown(
        f"<div class='footer-disclaimer'>{html.escape(APP_CONFIG['footer'])}</div>",
        unsafe_allow_html=True,
    )


def render_executive_view(frames: dict[str, pd.DataFrame], summary: dict[str, Any], display_recommendations: pd.DataFrame) -> None:
    recommendations = frames["recommendations"]
    triage = executive_triage_table(recommendations)

    callout_card(
        "Executive triage",
        "This view organizes demo-zone records into provisional review pathways; it does not approve incentives "
        "or calculate tax/fiscal impacts.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Zones screened", summary.get("zone_records_loaded", len(recommendations)), "Structured screening dataset")
    with c2:
        metric_card("More data required", executive_count(triage, "More data required"), "Source verification before use")
    with c3:
        metric_card("Legal review required", executive_count(triage, "legal|D4|R01|R02|R14|R20"), "D4 legal gate")

    c4, c5, c6 = st.columns(3)
    with c4:
        metric_card("Fiscal/FBR verification required", executive_count(triage, "fiscal|FBR|customs|D5|R09|R10|R13|R24"), "D5/FBR/customs gate")
    with c5:
        metric_card("Transition / grandfathering review", executive_count(triage, "transition|grandfather"), "Legal and fiscal caveats apply")
    with c6:
        metric_card(
            "Potential pilot-review flags",
            executive_count(triage, "Potential pilot-review flag"),
            "Subject to D4/D5 validation",
        )

    st.markdown("### Pathway Summary")
    pathway_summary = executive_pathway_summary(triage)
    render_pathway_summary_cards(pathway_summary)

    p2, p3 = st.columns(2)
    with p2:
        st.markdown("#### Dominant Reason Codes")
        reason_summary = executive_value_counts(recommendations, "reason_codes", limit=8)
        st.dataframe(reason_summary, width="stretch", hide_index=True)
    with p3:
        st.markdown("#### Dominant Open Gates")
        gate_summary = executive_value_counts(recommendations, "open_validation_gates", split_pipe=True, limit=8)
        st.dataframe(gate_summary, width="stretch", hide_index=True)

    selected_filter = st.radio(
        "Filter provisional review pathways",
        EXECUTIVE_FILTER_OPTIONS,
        horizontal=True,
        label_visibility="collapsed",
    )
    filtered = triage[executive_filter_mask(triage, selected_filter)]

    st.markdown("### Portfolio Triage")
    st.dataframe(filtered, width="stretch", hide_index=True)
    st.caption(
        f"Showing {len(filtered)} of {len(triage)} zones. Use Case Review to open a focused walkthrough case."
    )


def render_zone_explorer(frames: dict[str, pd.DataFrame], display_recommendations: pd.DataFrame) -> None:
    st.markdown("### Zone Explorer")
    st.info(APP_CONFIG["additionality_note"])
    explorer = display_recommendations.merge(
        frames["zones"],
        on=["zone_id", "zone_name", "province", "operational_status"],
        how="left",
        suffixes=("", "_source"),
    )

    if demo_mode_active():
        cases = demo_case_catalog(frames["recommendations"])
        case_ids = [str(case["zone_id"]) for case in cases]
        filtered = explorer[explorer["zone_id"].astype(str).isin(case_ids)].copy()
        for case in cases:
            mask = filtered["zone_id"].astype(str) == str(case["zone_id"])
            filtered.loc[mask, "Demo Case"] = case["label"]
            if not real_zone_names_visible():
                filtered.loc[mask, "zone_name"] = case["anonymous_label"]
                if "developer_name" in filtered.columns:
                    filtered.loc[mask, "developer_name"] = "Synthetic demo dataset"
        st.markdown("### Demo Cases")
        st.caption("Synthetic demo view shows the four-case walkthrough instead of full dataset filters.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        province_filter = c1.multiselect(
            "Province", filtered_options(explorer["province"]), default=filtered_options(explorer["province"])
        )
        activity_filter = c2.multiselect(
            "Activity classification",
            filtered_options(explorer["Activity Classification"]),
            default=filtered_options(explorer["Activity Classification"]),
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
            & explorer["Activity Classification"].isin(activity_filter)
            & explorer["Data Confidence"].isin(confidence_filter)
            & explorer["Provisional Treatment"].isin(treatment_filter)
        ]

    table_columns = [
        "zone_id",
        "zone_name",
        "province",
        "Activity Classification",
        "Data Confidence",
        "Provisional Treatment",
        "Open Gates",
    ]
    if demo_mode_active() and "Demo Case" in filtered.columns:
        table_columns = ["Demo Case", "Activity Classification", "Data Confidence", "Provisional Treatment", "Open Gates"]
    st.dataframe(
        filtered[[column for column in table_columns if column in filtered.columns]].rename(
            columns={
                "zone_id": "Zone ID",
                "zone_name": "Zone",
                "province": "Province",
                "Open Gates": "Open validation gates",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    if filtered.empty:
        st.info("No zones match the current filters.")
        return

    if demo_mode_active():
        selected_zone_id = current_demo_zone_id(frames["recommendations"])
        selected_rows = filtered[filtered["zone_id"].astype(str) == str(selected_zone_id)]
        rec = selected_rows.iloc[0] if not selected_rows.empty else filtered.iloc[0]
    else:
        selected = st.selectbox("Selected zone", filtered["zone_name"].tolist())
        rec = filtered[filtered["zone_name"] == selected].iloc[0]

    st.markdown("### Selected Zone")
    render_zone_header(rec)

    st.markdown("### Zone Summary")
    st.dataframe(selected_zone_summary(rec), width="stretch", hide_index=True)

    st.markdown("### Interpretation")
    with st.container(border=True):
        st.dataframe(selected_zone_interpretation(rec), width="stretch", hide_index=True)

    render_calibration_output(rec)

    if not demo_mode_active():
        with st.expander("Audit trail / raw record"):
            st.dataframe(friendly_dataframe(filtered[filtered["zone_name"] == selected]), width="stretch", hide_index=True)


def render_recommendation_engine(
    frames: dict[str, pd.DataFrame],
    reason_codes: dict[str, str],
    recommendations: pd.DataFrame,
    display_recommendations: pd.DataFrame,
) -> None:
    st.markdown("### Recommendation Engine")
    st.caption("Reason-coded provisional screening logic. Human, D4 legal, and D5 fiscal review remain mandatory.")

    page_display = demo_display_rows(display_recommendations, recommendations) if demo_mode_active() else display_recommendations
    st.dataframe(
        executive_table(page_display),
        width="stretch",
        hide_index=True,
    )

    if demo_mode_active():
        case = current_demo_case(recommendations)
        selected_zone_id = case.get("zone_id") if case else None
        rec = recommendations[recommendations["zone_id"].astype(str) == str(selected_zone_id)].iloc[0]
        rec = anonymized_demo_record(rec, case)
        display_rec = display_recommendations[display_recommendations["zone_id"].astype(str) == str(selected_zone_id)].iloc[0].copy()
        if not real_zone_names_visible() and case:
            display_rec["zone_name"] = case["anonymous_label"]
        st.info(f"Synthetic demo case: {case['label'] if case else 'Selected demo case'}")
    else:
        selected = st.selectbox("Selected zone for explanation", recommendations["zone_name"].tolist())
        rec = recommendations[recommendations["zone_name"] == selected].iloc[0]
        display_rec = display_recommendations[display_recommendations["zone_id"] == rec["zone_id"]].iloc[0]

    st.markdown("### Selected Zone Card")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Zone", visible_text(rec["zone_name"]))
    c2.metric("Province", visible_text(rec["province"]))
    c3.metric("Reported Status", visible_text(rec.get("operational_status", "Not available"))[:42])
    c4.metric("Activity Classification", activity_label(rec["activity_category"]))

    c5, c6, c7 = st.columns(3)
    c5.metric("Data Confidence", visible_text(display_rec["Data Confidence"]))
    c6.metric("Legal Status", visible_text(rec.get("legal_status", display_rec["Legal Status"])))
    c7.metric("Fiscal Status", visible_text(rec.get("fiscal_exposure_status", display_rec["Fiscal Status"])))

    st.info(APP_CONFIG["additionality_note"])

    c8, c9, c10 = st.columns(3)
    c8.metric("Additionality Confidence", visible_text(rec.get("additionality_confidence", "Not yet validated")))
    c9.metric("Incentive-Effectiveness Confidence", visible_text(rec.get("incentive_effectiveness_confidence", "Not yet validated")))
    c10.metric("Net Fiscal/Economic Impact", visible_text(rec.get("net_fiscal_economic_impact", "Not yet validated")))

    c10a, c10b, c10c = st.columns(3)
    c10a.metric("Counterfactual Status", visible_text(rec.get("counterfactual_status", "Not assessed")))
    c10b.metric("Displacement Risk", visible_text(rec.get("displacement_risk", "Not yet validated")))
    c10c.metric("Fiscal Return Confidence", visible_text(rec.get("fiscal_return_confidence", "Not yet validated")))

    c11, c12, c13 = st.columns(3)
    c11.metric("Fiscal Exposure Status", visible_text(rec.get("fiscal_exposure_status", "Not yet validated")))
    c12.metric("Compliance Status", visible_text(rec.get("compliance_status", "Requires validation")))
    c13.metric("Human Review", visible_text(rec.get("human_review_status", "Required")))

    st.markdown("### Screening Output Card")
    o1, o2, o3, o4 = st.columns(4)
    with o1:
        output_card("Provisional treatment", treatment_label(rec.get("provisional_treatment", rec.get("recommended_treatment", ""))))
    with o2:
        output_card("Open gates", compact_text(rec.get("open_validation_gates", rec.get("blocking_validation_requirements", ""))))
    with o3:
        output_card("Next action", compact_text(rec.get("next_actions", "Human review required.")))
    with o4:
        output_card("Validator", compact_text(rec.get("validator_owner", "BOI / SEZA / FBR / Finance / legal team / REMIT")))

    st.caption("Every screening output is provisional, subject to validation, and requires human review.")

    render_calibration_output(rec)

    with st.expander("Basis, gates, and reason codes", expanded=False):
        st.markdown("#### Conditions / Gates")
        render_bullets(split_pipe_text(rec.get("conditions_gates", "")))

        st.markdown("#### Why")
        st.info(
            "Observed activity may reflect real on-ground progress, but the framework does not infer causation. "
            "Before fiscal support is considered, the team should test whether activity was caused or accelerated "
            "by SEZ treatment, would have occurred anyway, or reflects relocation/reclassification."
        )
        st.write(display_memo_text(rec.get("why", "")))

        st.markdown("#### Open Validation Gates")
        render_bullets(split_pipe_text(rec.get("open_validation_gates", rec.get("blocking_validation_requirements", ""))))

        st.markdown("#### Main Blockers")
        render_bullets(split_pipe_text(rec.get("main_blockers", "")))

        st.markdown("#### Main Reason Codes")
        st.dataframe(decode_reason_codes(rec["reason_codes"], reason_codes), width="stretch", hide_index=True)

        st.markdown("#### Data Gaps")
        render_bullets(split_pipe_text(rec.get("data_gaps", "")))

    c14, c15 = st.columns(2)
    with c14:
        st.markdown("### Next Required Action")
        st.write(display_action_text(rec.get("next_actions", "Human review required.")))
    with c15:
        st.markdown("### Validator / Owner")
        st.write(visible_text(rec.get("validator_owner", "BOI / SEZA / FBR / Finance / legal team / REMIT")))

    st.markdown("### Human Review")
    st.write("Required")

    if not demo_mode_active():
        with st.expander("Audit trail / technical details"):
            st.markdown("#### Validation and Scoring")
            scoring = pd.DataFrame(
                [
                    {
                        "Data Confidence Score": rec.get("data_confidence_score"),
                        "Data Confidence Band": rec.get("data_confidence_band"),
                        "Open Validation Gates": rec.get("open_validation_gates", format_gates(rec.get("hard_gates_triggered"))),
                        "Reason Codes": rec.get("reason_codes"),
                        "Validator / Owner": rec.get("validator_owner"),
                    }
                ]
            )
            st.dataframe(scoring, width="stretch", hide_index=True)

            st.markdown("#### Raw Screening Output Record")
            raw = pd.DataFrame([rec.to_dict()])
            raw["recommended_treatment"] = display_rec["Provisional Treatment"]
            st.dataframe(friendly_dataframe(raw), width="stretch", hide_index=True)

            source = frames["zones"][frames["zones"]["zone_id"] == rec["zone_id"]]
            if not source.empty:
                st.markdown("#### Source Fields")
                st.dataframe(friendly_dataframe(source), width="stretch", hide_index=True)


def selected_demo_context(
    frames: dict[str, pd.DataFrame],
    display_recommendations: pd.DataFrame,
) -> tuple[dict[str, object] | None, pd.Series, pd.Series]:
    recommendations = frames["recommendations"]
    case = current_demo_case(recommendations)
    if case is None:
        rec = recommendations.iloc[0].copy()
        display_rec = display_recommendations.iloc[0].copy()
        return None, rec, display_rec

    selected_zone_id = case.get("zone_id")
    rec_rows = recommendations[recommendations["zone_id"].astype(str) == str(selected_zone_id)]
    display_rows = display_recommendations[display_recommendations["zone_id"].astype(str) == str(selected_zone_id)]
    rec = rec_rows.iloc[0].copy() if not rec_rows.empty else recommendations.iloc[0].copy()
    display_rec = display_rows.iloc[0].copy() if not display_rows.empty else display_recommendations.iloc[0].copy()

    rec = anonymized_demo_record(rec, case)
    display_rec["zone_name"] = case["anonymous_label"]
    if "developer_name" in display_rec.index:
        display_rec["developer_name"] = "Synthetic demo dataset"

    source_rows = frames["zones"][frames["zones"]["zone_id"].astype(str) == str(selected_zone_id)]
    if not source_rows.empty:
        source = source_rows.iloc[0]
        for column, value in source.items():
            if column not in display_rec.index or display_value(display_rec.get(column), "") == "":
                display_rec[column] = value
        display_rec["zone_name"] = case["anonymous_label"]
        display_rec["developer_name"] = "Synthetic demo dataset"

    return case, rec, display_rec


def case_review_pathway(row: pd.Series) -> str:
    return executive_pathway_text(row)


def case_review_text_blob(row: pd.Series) -> str:
    fields = [
        "provisional_treatment",
        "recommended_treatment",
        "open_validation_gates",
        "blocking_validation_requirements",
        "main_blockers",
        "reason_codes",
        "next_actions",
        "required_data_action",
        "required_legal_action",
        "required_fbr_action",
        "hard_gates_triggered",
        "fiscal_data_status",
        "fiscal_exposure_status",
        "legal_status",
    ]
    return " ".join(str(row.get(field, "")) for field in fields).lower()


def default_case_review_zone_id(recommendations: pd.DataFrame) -> str:
    if recommendations.empty:
        return ""
    priorities = [
        "fbr|fiscal|customs|d5|r09|r13",
        "legal|d4|r01|r02|r14|r20",
        "more data required|low_data_confidence|r08",
    ]
    text = recommendations.apply(case_review_text_blob, axis=1)
    for pattern in priorities:
        matches = recommendations[text.str.contains(pattern, case=False, regex=True, na=False)]
        if not matches.empty:
            return str(matches.iloc[0].get("zone_id", matches.index[0]))
    return str(recommendations.iloc[0].get("zone_id", recommendations.index[0]))


def case_review_selector_label(row: pd.Series) -> str:
    zone = display_value(row.get("zone_name"), "Selected zone")
    province = display_value(row.get("province"), "")
    pathway = case_review_pathway(row)
    if province:
        return f"{zone} - {province} - {pathway}"
    return f"{zone} - {pathway}"


def case_review_selected_row(recommendations: pd.DataFrame) -> pd.Series:
    if recommendations.empty:
        return pd.Series(dtype=object)
    zone_ids = [str(value) for value in recommendations["zone_id"].astype(str).tolist()]
    if st.session_state.get("case_review_zone_id") not in zone_ids:
        st.session_state.case_review_zone_id = default_case_review_zone_id(recommendations)
    label_map = {
        str(row.get("zone_id")): case_review_selector_label(row)
        for _, row in recommendations.iterrows()
    }
    st.selectbox(
        "Select case",
        zone_ids,
        key="case_review_zone_id",
        format_func=lambda zone_id: label_map.get(str(zone_id), str(zone_id)),
    )
    selected = recommendations[recommendations["zone_id"].astype(str) == str(st.session_state.case_review_zone_id)]
    if selected.empty:
        return recommendations.iloc[0].copy()
    return selected.iloc[0].copy()


def fiscal_validation_required(row: pd.Series) -> bool:
    values = [
        str(row.get("fiscal_exposure_level", "")).strip().lower(),
        str(row.get("fiscal_data_status", "")).strip().lower(),
        str(row.get("fiscal_exposure_status", "")).strip().lower(),
    ]
    text = case_review_text_blob(row)
    return any(value in {"", "unknown", "missing", "placeholder", "not yet validated"} for value in values) or bool(
        re.search(r"fbr|fiscal|customs|d5|r09|r13", text)
    )


def legal_review_required(row: pd.Series) -> bool:
    legal_risk = str(row.get("legal_risk_level", "")).strip().lower()
    legal_status = str(row.get("legal_status", "")).strip().lower()
    text = case_review_text_blob(row)
    return legal_risk in {"", "unknown", "high", "not yet validated"} or "review" in legal_status or bool(
        re.search(r"legal|d4|r01|r02|r14|r20", text)
    )


def additionality_caveat_required(row: pd.Series) -> bool:
    additionality = str(row.get("additionality_confidence", "")).strip().lower()
    counterfactual = str(row.get("counterfactual_status", "")).strip().lower()
    effectiveness = str(row.get("incentive_effectiveness_confidence", "")).strip().lower()
    unknown_values = {"", "unknown", "not assessed", "not yet validated", "weak"}
    return additionality in unknown_values or counterfactual in unknown_values or effectiveness in unknown_values


def case_review_gates(row: pd.Series) -> list[str]:
    gates: list[str] = []
    for field in ["open_validation_gates", "blocking_validation_requirements", "conditions_gates"]:
        gates.extend(split_pipe_text(row.get(field, "")))
    if fiscal_validation_required(row):
        gates.append("D5/FBR fiscal exposure validation required before calibration use.")
    if legal_review_required(row):
        gates.append("D4 legal review required before treatment classification.")
    if additionality_caveat_required(row):
        gates.append("Reported activity is not treated as proof of additionality or incentive effectiveness.")
    unique: list[str] = []
    for gate in gates:
        clean = visible_text(gate)
        if clean and clean not in unique:
            unique.append(clean)
    return unique


def case_review_blockers(row: pd.Series) -> list[str]:
    blockers = split_pipe_text(row.get("main_blockers", ""))
    blockers.extend(split_pipe_text(row.get("data_gaps", "")))
    unique: list[str] = []
    for blocker in blockers:
        clean = visible_text(blocker)
        if clean and clean not in unique:
            unique.append(clean)
    return unique


def case_review_next_actions(row: pd.Series) -> list[str]:
    actions = []
    for field in ["next_actions", "required_data_action", "required_legal_action", "required_fbr_action"]:
        actions.extend(split_pipe_text(row.get(field, "")) or [row.get(field, "")])
    unique: list[str] = []
    for action in actions:
        clean = display_action_text(action)
        if clean and clean != "Not available" and clean not in unique:
            unique.append(clean)
    return unique or ["Human review required before fiscal, legal, calibration, or pilot use."]


def render_case_memo_card(title: str, body: object) -> None:
    st.markdown(
        "<div class='case-memo-card'>"
        f"<div class='case-memo-title'>{html.escape(visible_text(title))}</div>"
        f"<div class='case-memo-body'>{html.escape(visible_text(body))}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_case_header_card(row: pd.Series, pathway: str) -> None:
    confidence = visible_text(str(row.get("data_confidence_band", "")).replace("_", " ").title())
    activity = activity_label(row.get("activity_category"))
    badges = "".join(
        [
            badge_html(confidence, confidence_tone(confidence)),
            badge_html("Human review required", "warning"),
            badge_html(pathway, pathway_tone(pathway)),
        ]
    )
    st.markdown(
        "<div class='case-header-card'>"
        f"<div class='case-header-title'>{html.escape(display_value(row.get('zone_name'), 'Selected zone'))}</div>"
        "<div class='case-header-meta'>"
        f"<span><strong>Province:</strong> {html.escape(display_value(row.get('province')))}</span>"
        f"<span><strong>Activity:</strong> {html.escape(activity)}</span>"
        f"<span><strong>Reported status:</strong> {html.escape(display_value(row.get('operational_status')))}</span>"
        "</div>"
        f"<div class='badge-row'>{badges}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_reason_code_pills(codes: object, reason_codes: dict[str, str]) -> None:
    parts = split_reason_codes(codes)
    if not parts:
        st.write("No reason codes were generated for this case.")
        return
    html_rows = []
    for code in parts:
        reason = display_reason_text(reason_codes.get(code, "Unmapped reason code"))
        html_rows.append(
            "<div class='reason-code-row'>"
            f"<span class='reason-pill'>{html.escape(code)}</span>"
            f"<span class='reason-text'>{html.escape(reason)}</span>"
            "</div>"
        )
    st.markdown("".join(html_rows), unsafe_allow_html=True)


def render_support_context(row: pd.Series) -> None:
    st.caption("Illustrative only - not an incentive award.")
    cols = st.columns(4)
    items = [
        ("Support treatment", row.get("illustrative_support_treatment")),
        ("Instrument", row.get("illustrative_instrument_options")),
        ("Fiscal cap", row.get("fiscal_cap")),
        ("Sunset", row.get("sunset")),
    ]
    for col, (label, value) in zip(cols, items):
        with col:
            summary_card(label, display_value(value))


def confidence_band_counts(confidence: pd.DataFrame) -> dict[str, int]:
    bands = confidence.get("data_confidence_band", pd.Series(dtype=str)).fillna("").astype(str).str.lower()
    return {
        "high": int(bands.eq("high").sum()),
        "medium": int(bands.eq("medium").sum()),
        "low": int(bands.eq("low").sum()),
        "do_not_use": int(bands.eq("do_not_use").sum()),
    }


def combined_validation_logs(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    logs = []
    if "issues" in frames and not frames["issues"].empty:
        logs.append(frames["issues"].copy())
    if "contradictions" in frames and not frames["contradictions"].empty:
        logs.append(frames["contradictions"].copy())
    if not logs:
        return pd.DataFrame()
    return pd.concat(logs, ignore_index=True, sort=False)


def critical_high_validation_count(frames: dict[str, pd.DataFrame]) -> int:
    logs = combined_validation_logs(frames)
    if logs.empty or "severity" not in logs.columns:
        return 0
    severity = logs["severity"].fillna("").astype(str).str.lower()
    return int(severity.isin(["critical", "high"]).sum())


def source_scope_issue_count(frames: dict[str, pd.DataFrame]) -> int:
    logs = combined_validation_logs(frames)
    if logs.empty:
        return 0
    text = pd.Series([""] * len(logs), index=logs.index)
    for column in ["field_name", "issue_type", "issue_description", "model_impact", "recommended_fix"]:
        if column in logs.columns:
            text = text + " " + logs[column].fillna("").astype(str)
    return int(text.str.contains("source_scope|source scope|universe|44/54|coverage|definition", case=False, regex=True).sum())


def confidence_display_table(confidence: pd.DataFrame) -> pd.DataFrame:
    columns = ["zone_name", "data_confidence_band", "data_confidence_score", "confidence_reason"]
    table = confidence[[column for column in columns if column in confidence.columns]].copy()
    if "data_confidence_band" in table.columns:
        table["data_confidence_band"] = table["data_confidence_band"].apply(
            lambda value: visible_text(str(value).replace("_", " ").title(), "Not available")
        )
    if "data_confidence_score" in table.columns:
        table["data_confidence_score"] = pd.to_numeric(table["data_confidence_score"], errors="coerce").round(3)
    for column in table.columns:
        if pd.api.types.is_object_dtype(table[column]) or pd.api.types.is_string_dtype(table[column]):
            table[column] = table[column].apply(display_value)
    return table.rename(
        columns={
            "zone_name": "Zone",
            "data_confidence_band": "Confidence band",
            "data_confidence_score": "Confidence score",
            "confidence_reason": "Confidence reason",
        }
    )


def high_priority_validation_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    validation_table = validation_display_table(frames)
    if validation_table.empty or "Severity" not in validation_table.columns:
        return validation_table
    return validation_table[validation_table["Severity"].isin(["Blocking", "Material"])].copy()


def audit_flags_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    if "audit_flags" in frames and not frames["audit_flags"].empty:
        return friendly_dataframe(frames["audit_flags"])
    if "audit" in frames and not frames["audit"].empty:
        return friendly_dataframe(frames["audit"])
    return pd.DataFrame()


def render_case_review(
    frames: dict[str, pd.DataFrame],
    reason_codes: dict[str, str],
    display_recommendations: pd.DataFrame,
) -> None:
    recommendations = frames["recommendations"]
    if recommendations.empty:
        st.info("No case-review records were generated by the current pipeline run.")
        return

    st.markdown("### Case Review")
    st.caption(
        "Human-review memo for one zone record. The screening output indicates a provisional review pathway; it does "
        "not decide entitlement or set tax/fiscal treatment."
    )

    rec = case_review_selected_row(recommendations)
    pathway = case_review_pathway(rec)
    gates = case_review_gates(rec)
    blockers = case_review_blockers(rec)
    actions = case_review_next_actions(rec)

    render_case_header_card(rec, pathway)

    st.markdown("#### Review Pathway")
    render_case_memo_card("Review pathway", pathway)
    render_support_context(rec)

    st.markdown("#### Why This Was Flagged")
    why_text = display_memo_text(rec.get("why", "Human review required before fiscal, legal, calibration, or pilot use."))
    render_case_memo_card("Basis for pathway", why_text)
    caveats = []
    if fiscal_validation_required(rec):
        caveats.append("D5/FBR fiscal exposure validation required before calibration use.")
    if legal_review_required(rec):
        caveats.append("D4 legal review required before treatment classification.")
    if additionality_caveat_required(rec):
        caveats.append("Reported activity is not treated as proof of additionality or incentive effectiveness.")
    if caveats:
        st.markdown("##### Required caveats")
        render_bullets(caveats)

    st.markdown("#### Reason Codes")
    render_reason_code_pills(rec.get("reason_codes"), reason_codes)

    st.markdown("#### Open Gates")
    render_bullets(gates)
    if blockers:
        with st.expander("Main blockers and data gaps", expanded=False):
            render_bullets(blockers)

    st.markdown("#### Next Action and Validation Owner")
    n1, n2 = st.columns([0.66, 0.34])
    with n1:
        render_bullets(actions)
    with n2:
        output_card("Validation owner", display_value(rec.get("validator_owner"), "BOI / SEZA / FBR / Finance / legal team / REMIT"))
        output_card("Human review", "Required")


def render_data_confidence_mvp(frames: dict[str, pd.DataFrame], summary: dict[str, Any]) -> None:
    st.markdown("### Data Confidence")
    st.caption(
        "This page identifies whether a zone record is usable for provisional screening, requires source-row "
        "verification, or should be kept out of calibration use."
    )

    confidence = frames.get("confidence", pd.DataFrame())
    band_counts = confidence_band_counts(confidence)
    counts = validation_metric_counts(frames)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("High confidence", band_counts["high"], "Usable for provisional screening")
    with c2:
        metric_card("Medium confidence", band_counts["medium"], "Usable with caveats")
    with c3:
        metric_card("Low confidence", band_counts["low"], "More verification needed")
    with c4:
        metric_card("Do not use", band_counts["do_not_use"], "Keep out of calibration use")

    c5, c6 = st.columns(2)
    with c5:
        metric_card("Critical/high validation flags", critical_high_validation_count(frames), "Blocking or material source checks")
    with c6:
        metric_card("Source-scope issues", source_scope_issue_count(frames), "Coverage, universe, or definition limits")

    callout_card(
        "Dataset scope note",
        "Current demo uses 35 structured screening records; do not generalize to the full "
        "44/54-zone universe without reconciliation.",
    )

    st.markdown("#### Confidence by Zone")
    st.dataframe(confidence_display_table(confidence), width="stretch", hide_index=True)

    st.markdown("#### Critical / High Validation Flags")
    st.caption(
        "Validation flags are not app errors. They identify fields requiring source verification before fiscal, legal, "
        "calibration, or pilot use."
    )
    high_priority = high_priority_validation_table(frames)
    st.dataframe(high_priority, width="stretch", hide_index=True)

    st.markdown("#### Confidence Scoring Reference")
    scoring = pd.DataFrame(
        [
            {"Component": "Source reliability", "Role": "Checks whether source lineage is present and credible."},
            {"Component": "Completeness", "Role": "Checks critical fields needed for screening and validation."},
            {"Component": "Internal consistency", "Role": "Checks acreage, status, and field-level logic within a record."},
            {"Component": "Source and status consistency", "Role": "Checks the structured screening dataset, status fields, and coverage notes."},
            {"Component": "Recency", "Role": "Checks whether current-period source notes are present."},
        ]
    )
    banding = pd.DataFrame(
        [
            {"Band": "High", "Use": "Usable for screening."},
            {"Band": "Medium", "Use": "Usable with caveats."},
            {"Band": "Low", "Use": "More data required."},
            {"Band": "Do not use for decision", "Use": "Source verification required before policy use."},
        ]
    )
    s1, s2 = st.columns(2)
    s1.dataframe(scoring, width="stretch", hide_index=True)
    s2.dataframe(banding, width="stretch", hide_index=True)

    with st.expander("Show full data-quality issue log", expanded=False):
        st.dataframe(friendly_dataframe(frames.get("issues", pd.DataFrame())), width="stretch", hide_index=True)

    with st.expander("Show cross-source/status conflicts", expanded=False):
        st.caption("Source-scope and consistency flags.")
        st.dataframe(friendly_dataframe(frames.get("contradictions", pd.DataFrame())), width="stretch", hide_index=True)

    with st.expander("Show field completeness", expanded=False):
        st.dataframe(friendly_dataframe(frames.get("field_completeness", pd.DataFrame())), width="stretch", hide_index=True)

    audit_flags = audit_flags_table(frames)
    if not audit_flags.empty:
        with st.expander("Show audit flags", expanded=False):
            st.dataframe(audit_flags, width="stretch", hide_index=True)

    with st.expander("Audit trail / technical details", expanded=False):
        st.metric("Fields with missing values", counts["fields_with_gaps"])
        st.markdown("##### Source processing log")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Processing Step": "Load structured screening dataset",
                        "Status": f"{summary['zone_records_loaded']} zone records loaded for screening.",
                    },
                    {
                        "Processing Step": "Apply validation checks",
                        "Status": f"{summary['data_quality_issue_count']} validation flags generated.",
                    },
                    {
                        "Processing Step": "Check source and status validation flags",
                        "Status": f"{summary['contradiction_count']} source-scope or consistency flags generated.",
                    },
                ]
            ),
            width="stretch",
            hide_index=True,
        )


def render_export_memo(
    frames: dict[str, pd.DataFrame],
    summary: dict[str, Any],
    reason_codes: dict[str, str],
    display_recommendations: pd.DataFrame,
) -> None:
    st.markdown("### Work-Product Exports")
    callout_card(
        "Structured outputs",
        "Generate CSV extracts and a selected-zone screening note for the live walkthrough.",
    )

    recommendations = frames["recommendations"]
    cases = demo_case_catalog(recommendations)
    if cases:
        case_map = {str(case["key"]): case for case in cases}
        valid_keys = list(case_map)
        if st.session_state.get("demo_case_key") not in valid_keys:
            st.session_state.demo_case_key = valid_keys[0]
        st.selectbox(
            "Screening note case",
            valid_keys,
            key="demo_case_key",
            format_func=lambda key: str(case_map[key]["anonymous_label"]),
        )

    case, selected_rec, _display_rec = selected_demo_context(frames, display_recommendations)
    selected_file_token = safe_file_token(case.get("key") if case else selected_rec.get("zone_id", "selected_zone"))
    export_display = demo_display_rows(display_recommendations, recommendations)
    triage_export = executive_table(export_display)
    validation_export = demo_scope_table(validation_display_table(frames), recommendations)
    metadata = export_metadata(summary, selected_rec)

    with st.container(border=True):
        st.markdown("#### Source / Audit Metadata")
        st.dataframe(pd.DataFrame([metadata]), width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Export Executive Triage Table as CSV",
            data=dataframe_to_csv_bytes(triage_export),
            file_name="executive_triage_table.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "Export Validation Flags as CSV",
            data=dataframe_to_csv_bytes(validation_export),
            file_name="validation_flags.csv",
            mime="text/csv",
        )

    st.markdown("#### Selected-Zone Screening Note")
    if st.button("Generate selected-zone screening note"):
        st.session_state.export_selected_zone_id = str(selected_rec.get("zone_id", selected_file_token))
        st.session_state.export_memo_markdown = selected_zone_memo(selected_rec, reason_codes, summary)
        st.session_state.export_memo_txt = selected_zone_memo(selected_rec, reason_codes, summary, plain_text=True)

    if st.session_state.get("export_memo_markdown"):
        memo_markdown = st.session_state.export_memo_markdown
        memo_txt = st.session_state.export_memo_txt
        st.markdown("##### Export Preview")
        with st.container(border=True):
            st.markdown(memo_markdown)
        m1, m2 = st.columns(2)
        with m1:
            st.download_button(
                "Export Selected-Zone Explanation as Markdown",
                data=memo_markdown.encode("utf-8"),
                file_name=f"{selected_file_token}_prototype_screening_note.md",
                mime="text/markdown",
            )
        with m2:
            st.download_button(
                "Export Selected-Zone Explanation as TXT",
                data=memo_txt.encode("utf-8"),
                file_name=f"{selected_file_token}_prototype_screening_note.txt",
                mime="text/plain",
            )
    else:
        callout_card("Export preview", "Select a case and generate the screening note to preview it before downloading.")

    with st.expander("CSV preview tables", expanded=False):
        st.markdown("##### Executive triage table")
        st.dataframe(triage_export, width="stretch", hide_index=True)
        st.markdown("##### Validation flags")
        st.dataframe(validation_export, width="stretch", hide_index=True)


def render_about_limitations(summary: dict[str, Any]) -> None:
    st.markdown("### About / Limitations")
    st.caption("Scope notes for presenting the prototype safely in a short walkthrough.")

    with st.expander("Public demo posture", expanded=True):
        st.write(f"**{DATA_PROFILE_LABEL}.** The public/demo build is for workflow demonstration.")
        st.write(NON_DECISION_STATEMENT)
    with st.expander("Scope and guardrails", expanded=False):
        st.write(
            "Any support-related output is provisional and subject to D4 legal review and D5/FBR/customs verification. "
            "No final tax rates or incentive awards are calculated."
        )
    with st.expander("Dataset limits", expanded=False):
        st.write(
            "This MVP uses hypothetical synthetic zones for workflow demonstration. Do not treat demo screening "
            "outputs as BOI, SEZA, FBR, Finance, legal, developer, or enterprise records."
        )
        st.write(REAL_USE_REQUIREMENTS)
    with st.expander("Legal, fiscal, and validation requirements", expanded=False):
        st.write(
            "D4 legal review and D5/FBR validation are required before any policy use. Human review is required for "
            "every output."
        )
        st.write(APP_CONFIG["additionality_note"])
    with st.expander("What the prototype does not do", expanded=False):
        st.write(
            "The app is a decision-support layer around triage, validation, and structured exports. It is not a legal opinion, "
            "fiscal estimate, tax calculation, incentive clearance, or replacement for BOI, FBR, Finance Division, SEZA, "
            "legal counsel, IMF review, programme review, or human review."
        )

    with st.expander("Run summary", expanded=False):
        st.dataframe(pd.DataFrame([summary]), width="stretch", hide_index=True)


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
    c4.metric("Validation tables", "Created" if summary.get("placeholders_created") else "Present")

    note_card(
        "Structured dataset note",
        [
            "The current structured screening dataset is suitable for workflow demonstration. Exact row-level verification should use validated source documents before policy use.",
            "The current structured screening dataset covers 35 detected zone profile records and 35 indicator records based on the source digest.",
            "Legal, enterprise compliance, and fiscal exposure fields remain pending D4/D5 validation.",
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
    st.dataframe(friendly_dataframe(demo_scope_table(fiscal, frames["recommendations"])), width="stretch", hide_index=True)

    if not demo_mode_active():
        with st.expander("Audit trail / technical details"):
            assumptions = pd.DataFrame(
                [
                    {
                        "Assumption": "Fiscal exposure fields are pending validation",
                        "Decision Connection": "D5/FBR/customs verification required before fiscal-cost or support review.",
                    },
                    {
                        "Assumption": "Legal status fields are pending validation",
                        "Decision Connection": "D4 legal review required before treatment screening or phase-out analysis.",
                    },
                    {
                        "Assumption": "Current demo is a 35-zone structured screening dataset",
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
        "The current structured screening dataset is suitable for screening and demonstration. Exact row-level verification should use "
        "the original workbook and source documents before policy use."
    )
    st.caption(
        "Validation flags are not necessarily errors. They identify fields requiring source verification before fiscal, "
        "legal, calibration, or pilot use."
    )

    counts = validation_metric_counts(frames)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Validation flags", summary["data_quality_issue_count"])
    c2.metric("Cross-source/status conflicts", summary["contradiction_count"])
    c3.metric("Missing field checks", counts["missing_fields"])
    c4.metric("Coverage / definition warnings", counts["coverage_warnings"])
    c5.metric("Row-level verification fields", counts["row_level_verification"])

    st.markdown("### Source Confidence Summary")
    validation_table = demo_scope_table(validation_display_table(frames), frames["recommendations"])
    severity_counts = validation_table["Severity"].value_counts().rename_axis("Severity").reset_index(
        name="Validation flags"
    )
    st.dataframe(severity_counts, width="stretch", hide_index=True)

    note_card(
        "Validation flag types covered",
        [
            "Missing fiscal data, missing legal data, and missing enterprise-level data.",
            "Conflicting zone names, possible duplicate zone records, and source-row verification requirements.",
            "Status mismatches, under-construction versus under-production mismatches, and acreage totals that do not reconcile.",
            "Coverage / definition issues and values requiring source verification.",
        ],
    )

    st.markdown("### Validation Flags")
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
            {"Component": "Cross-source consistency", "Use in Score": "Checks conflicts across the structured screening dataset, status fields, and coverage notes."},
            {"Component": "Recency", "Use in Score": "Checks whether current-period source notes are present."},
        ]
    )
    banding = pd.DataFrame(
        [
            {"Band": "High", "Use": "Usable for screening."},
            {"Band": "Medium", "Use": "Usable with caveats."},
            {"Band": "Low", "Use": "More data required."},
            {"Band": "Do not use", "Use": "Source verification required before policy use."},
        ]
    )
    c6, c7 = st.columns(2)
    c6.dataframe(scoring, width="stretch", hide_index=True)
    c7.dataframe(banding, width="stretch", hide_index=True)

    st.markdown("### Source Lineage")
    lineage_columns = ["zone_id", "zone_name", "source_file", "source_row"]
    lineage = frames["zones"][[column for column in lineage_columns if column in frames["zones"].columns]].copy()
    lineage = demo_scope_table(lineage, frames["recommendations"])
    st.dataframe(friendly_dataframe(lineage), width="stretch", hide_index=True)

    if not demo_mode_active():
        with st.expander("Audit trail / technical details"):
            st.metric("Fields with missing values", counts["fields_with_gaps"])
            st.dataframe(friendly_dataframe(frames["field_completeness"]), width="stretch", hide_index=True)
            st.dataframe(friendly_dataframe(frames["confidence"]), width="stretch", hide_index=True)
            processing_log = pd.DataFrame(
                [
                    {
                        "Processing Step": "Load structured screening dataset",
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
            st.markdown("#### Source processing log")
            st.dataframe(processing_log, width="stretch", hide_index=True)
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


def kpi_assurance_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Reported KPI": "Employment",
                "Possible verification signal": "EOBI / social security records; payroll records; field verification",
                "Source / owner": "EOBI / provincial social security institutions / enterprise / BOI / SEZA",
                "Confidence": "Not assessed",
                "Variance / concern": "Reported job counts may not match payroll, social security, or field verification records.",
                "Suggested action": "Verify before using for incentive continuation or expansion.",
                "Notes": "Use worker records and field checks as assurance evidence, not automatic incentive triggers.",
            },
            {
                "Reported KPI": "Production status",
                "Possible verification signal": "electricity / gas consumption; field or aerial survey; SEZ-MIS production status; site visit",
                "Source / owner": "Utilities / SEZA / BOI / site verification team",
                "Confidence": "Not assessed",
                "Variance / concern": "Reported production may reflect partial activity, test runs, or stale status labels.",
                "Suggested action": "Confirm active commercial production.",
                "Notes": "Utility and site signals support plausibility checks before pilot monitoring or calibration use.",
            },
            {
                "Reported KPI": "Construction progress",
                "Possible verification signal": "geospatial imagery; field survey; developer progress reports; utility connection status",
                "Source / owner": "Developer / SEZA / utilities / independent verifier",
                "Confidence": "Not assessed",
                "Variance / concern": "Construction reports may describe early works or boundary-wall-only progress rather than material construction.",
                "Suggested action": "Confirm construction is material and not boundary-wall-only.",
                "Notes": "Construction-stage zones should remain transition-review cases until production evidence is verified.",
            },
            {
                "Reported KPI": "Exports",
                "Possible verification signal": "customs/export records; FBR data; enterprise returns",
                "Source / owner": "Customs / FBR / enterprise / Finance Division",
                "Confidence": "Not assessed",
                "Variance / concern": "Self-reported exports may not reconcile with customs declarations or tax records.",
                "Suggested action": "FBR/customs validation required.",
                "Notes": "Export data should be source-validated before fiscal exposure or calibration scoring.",
            },
            {
                "Reported KPI": "Investment / CAPEX",
                "Possible verification signal": "audited financials; import records; customs declarations; invoices",
                "Source / owner": "Enterprise / auditor / customs / FBR / Finance Division",
                "Confidence": "Not assessed",
                "Variance / concern": "Reported investment may include committed, imported, invoiced, or installed amounts that are not equivalent.",
                "Suggested action": "Validate before cost-based support review.",
                "Notes": "Cost-based review requires verified additionality, fiscal exposure, and cap/sunset controls.",
            },
            {
                "Reported KPI": "Operational activity",
                "Possible verification signal": "utilities; broadband activity; logistics movement; tax filings",
                "Source / owner": "Utilities / telecom providers / logistics records / FBR / SEZA",
                "Confidence": "Not assessed",
                "Variance / concern": "Proxy signals can indicate plausibility but may not identify the enterprise, activity type, or incentive causation.",
                "Suggested action": "Use as plausibility check / audit trigger only.",
                "Notes": "Proxy indicators are assurance signals and should not directly determine incentive treatment.",
            },
        ],
        columns=[
            "Reported KPI",
            "Possible verification signal",
            "Source / owner",
            "Confidence",
            "Variance / concern",
            "Suggested action",
            "Notes",
        ],
    )


def kpi_status_legend() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Output status": "Not assessed", "Meaning": "No assurance evidence has been loaded or reviewed."},
            {"Output status": "Plausible but unverified", "Meaning": "Verification signals are directionally consistent but not source-validated."},
            {"Output status": "Verified", "Meaning": "Administrative or field evidence supports the reported KPI."},
            {"Output status": "Inconsistent / audit trigger", "Meaning": "Verification signals conflict with reported KPI or indicate review risk."},
            {"Output status": "Not enough data", "Meaning": "Evidence is too sparse or incomplete for assurance judgment."},
        ]
    )


def render_kpi_assurance(frames: dict[str, pd.DataFrame]) -> None:
    st.markdown("### KPI Assurance & Verification Signals")
    st.caption(
        "Traditional KPIs should drive performance assessment. Verification signals help assess whether reported KPIs "
        "deserve confidence and whether desk review or audit is needed."
    )
    st.warning(
        "Proxy indicators are audit-trigger and confidence indicators. They should not directly determine incentive treatment."
    )
    st.info("Calibration should reward verified, additional, fiscally defensible activity - not merely reported activity.")

    st.markdown("### KPI Assurance Matrix")
    st.dataframe(kpi_assurance_matrix(), width="stretch", hide_index=True)

    st.markdown("### Output Status")
    st.dataframe(kpi_status_legend(), width="stretch", hide_index=True)

    kpi = frames["zones"].merge(frames["activity"], on=["zone_id", "zone_name"], how="left")
    kpi = kpi.merge(frames["confidence"], on=["zone_id", "zone_name"], how="left")
    kpi["Readiness"] = kpi.apply(readiness_label, axis=1)
    kpi["KPI / Monitoring Need"] = kpi.apply(kpi_need, axis=1)
    kpi["Activity Classification"] = kpi["activity_category"].apply(activity_label)
    kpi["Data Confidence"] = kpi.apply(confidence_label, axis=1)

    if not demo_mode_active():
        with st.expander("Zone monitoring context"):
            columns = [
                "zone_id",
                "zone_name",
                "province",
                "Activity Classification",
                "Data Confidence",
                "under_production_area_acres",
                "under_construction_area_acres",
                "vacant_area_acres",
                "Readiness",
                "KPI / Monitoring Need",
            ]
            st.dataframe(friendly_dataframe(kpi, columns), width="stretch", hide_index=True)


def bool_label(value: object) -> str:
    return "Yes" if bool(value) else "No"


def scenario_gates_for(preset: str) -> dict[str, object]:
    if preset not in POSTURE_DEFAULTS:
        preset = "Broad diagnostic screen"
    return dict(POSTURE_DEFAULTS[preset])


def scenario_presets_table() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, config in SCENARIO_PRESETS.items():
        gates = config["gates"]
        rows.append(
            {
                "Scenario": name,
                "Behavior": config["behavior"],
                "Minimum confidence": str(gates["minimum_data_confidence_band_for_pilot"]).title(),
                "Legal low-risk gate": bool_label(gates["require_legal_low_risk_for_pilot"]),
                "Fiscal data gate": bool_label(gates["require_fiscal_data_for_pilot"]),
                "High fiscal-exposure block": bool_label(gates["block_high_fiscal_exposure"]),
                "Diagnostic only": bool_label(gates["diagnostic_only"]),
            }
        )
    return pd.DataFrame(rows)


def current_scenario_table(preset: str) -> pd.DataFrame:
    config = SCENARIO_PRESETS.get(preset, SCENARIO_PRESETS["Broad diagnostic screen"])
    gates = scenario_gates_for(preset)
    gate_labels = {
        "require_legal_low_risk_for_pilot": "Require low legal risk before pilot-review flag",
        "require_fiscal_data_for_pilot": "Require D5/FBR fiscal data before pilot-review flag",
        "block_high_fiscal_exposure": "Block cost-based review language when fiscal exposure is high",
        "include_construction_stage_transition_candidates": "Include construction-stage zones as transition-review flags",
        "minimum_data_confidence_band_for_pilot": "Minimum confidence band for pilot-review flag",
        "strict_data_confidence_for_all": "Apply minimum confidence gate across all treatments",
        "treat_unknown_developer_compliance_as_blocker": "Treat not-yet-validated developer compliance as blocker",
        "prefer_non_fiscal_when_additionality_uncertain": "Prefer non-fiscal path when additionality is weak or not yet validated",
        "diagnostic_only": "Label wider screen as diagnostic only",
    }
    rows = [
        {"Setting": "Scenario behavior", "Current value": config["behavior"]},
        {
            "Setting": "Weights / emphasis",
            "Current value": "; ".join(f"{visible_text(k.replace('_', ' ').title())}: {visible_text(v).title()}" for k, v in config["weights"].items()),
        },
    ]
    for key, label in gate_labels.items():
        value = gates.get(key)
        rows.append({"Setting": label, "Current value": value.title() if isinstance(value, str) else bool_label(value)})
    return pd.DataFrame(rows)


def run_scenario_for_zone(
    frames: dict[str, pd.DataFrame],
    zone_id: object,
    scenario: dict[str, object],
) -> pd.Series | None:
    recommendations = run_recommendation_engine(
        frames["zones"],
        frames["confidence"],
        frames["activity"],
        frames["legal"],
        frames["fiscal"],
        frames["issues"],
        scenario,
    )
    selected = recommendations[recommendations["zone_id"].astype(str) == str(zone_id)]
    if selected.empty:
        return None
    return selected.iloc[0]


def scenario_change_reason(base: pd.Series | None, current: pd.Series | None, preset: str) -> str:
    if current is None:
        return "No matching selected zone record was available for this scenario."
    if base is not None and str(current.get("recommended_treatment", "")) == str(base.get("recommended_treatment", "")):
        return "No change from the current assumption set."
    treatment = str(current.get("recommended_treatment", ""))
    gates = str(current.get("hard_gates_triggered", ""))
    if "Legal review" in treatment or "scenario_legal_low_risk_required" in gates:
        return "Legal-risk gates or not-yet-validated legal status drive the change."
    if "Fiscal/FBR" in treatment or "scenario_fiscal_data_required" in gates:
        return "Fiscal exposure, missing D5/FBR data, or high fiscal-risk posture drives the change."
    if "More data required" in treatment or "scenario_minimum_confidence_band" in gates:
        return "Data-confidence threshold or source-quality gate drives the change."
    if "Non-fiscal" in treatment:
        return "Additionality uncertainty or fiscal-risk posture shifts the output away from cost-based support review."
    if "Phase-out" in treatment:
        return "Weak activity evidence, idle land, or low additionality shifts the output away from pilot review."
    if "transition" in treatment.lower():
        return "Production or construction movement receives transition weight under this posture."
    return str(SCENARIO_PRESETS.get(preset, {}).get("behavior", "Scenario assumptions change the output."))


def scenario_sensitivity_table(
    frames: dict[str, pd.DataFrame],
    selected_zone_id: object,
    base_scenario: dict[str, object],
) -> pd.DataFrame:
    base = run_scenario_for_zone(frames, selected_zone_id, base_scenario)
    base_treatment = treatment_label(base.get("recommended_treatment", "")) if base is not None else ""
    rows: list[dict[str, object]] = []
    for name, config in SCENARIO_PRESETS.items():
        scenario = scenario_gates_for(name)
        scenario["policy_posture_preset"] = name
        current = run_scenario_for_zone(frames, selected_zone_id, scenario)
        treatment = treatment_label(current.get("recommended_treatment", "Not available")) if current is not None else "Not available"
        if bool(config["gates"].get("diagnostic_only")) and treatment != "Not available":
            treatment = f"{treatment} (diagnostic only)"
        rows.append(
            {
                "Scenario": visible_text(name),
                "Provisional treatment": visible_text(treatment),
                "Changed from base?": "Yes" if treatment.replace(" (diagnostic only)", "") != base_treatment else "No",
                "Main reason for change": visible_text(scenario_change_reason(base, current, name)),
            }
        )
    return pd.DataFrame(rows)


def scenario_examples_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Assumption change": "Legal risk increases to High",
                "Likely treatment change": "Legal review required",
                "Why it matters": "Legal or contractual constraints can block treatment design before fiscal calibration is useful.",
            },
            {
                "Assumption change": "Fiscal exposure is missing",
                "Likely treatment change": "Fiscal/FBR validation required",
                "Why it matters": "Cost-based support-review language should not be used until D5/FBR exposure data is validated.",
            },
            {
                "Assumption change": "Additionality confidence drops",
                "Likely treatment change": "Away from cost-based support review",
                "Why it matters": "Observed activity is not proof that SEZ treatment caused or accelerated investment.",
            },
            {
                "Assumption change": "Data confidence drops below threshold",
                "Likely treatment change": "More data required",
                "Why it matters": "Fiscal, legal, calibration, or pilot use needs source confidence above the selected gate.",
            },
            {
                "Assumption change": "Activity changes from production to allotment-only",
                "Likely treatment change": "Away from pilot review",
                "Why it matters": "Allotment-only movement is not evidence of productive use or incentive effectiveness.",
            },
        ]
    )


def render_scenario_settings(frames: dict[str, pd.DataFrame], summary: dict[str, Any]) -> None:
    st.markdown("### Scenario Settings")
    st.caption("Make policy posture assumptions visible and compare how provisional outputs change.")
    st.info(
        "The value of this prototype is not that it already knows the answer. The value is that it makes assumptions visible. "
        "If the team disagrees with an output, we can see whether the issue is the data, legal gate, fiscal assumption, "
        "KPI weight, or scenario setting."
    )

    st.markdown("#### Quick Scenario Presets")
    quick_presets = [
        ("Base", "Broad diagnostic screen"),
        ("IMF strict triage", "IMF strict triage"),
        ("Data-quality conservative", "Data-quality conservative"),
        ("Pilot-readiness screen", "Pilot-readiness screen"),
    ]
    quick_cols = st.columns(len(quick_presets))
    for col, (label, preset) in zip(quick_cols, quick_presets):
        with col:
            if st.button(label, key=f"quick_scenario_{preset}", use_container_width=True):
                st.session_state.policy_posture_preset = preset
                apply_posture_defaults()
                st.rerun()

    c1, c2 = st.columns([0.38, 0.62])
    with c1:
        st.selectbox(
            "Scenario preset",
            list(SCENARIO_PRESETS),
            key="policy_posture_preset",
            on_change=apply_posture_defaults,
        )
        active_config = SCENARIO_PRESETS.get(st.session_state.policy_posture_preset, SCENARIO_PRESETS["Broad diagnostic screen"])
        note_card(
            "Current assumption set",
            [
                f"Scenario: {st.session_state.policy_posture_preset}",
                active_config["behavior"],
                f"Potential pilot-review flags: {summary['possible_pilot_screen_candidates']}",
                f"More data required: {summary['more_data_required']}",
                "All outputs remain provisional and subject to D4 legal review and D5 fiscal verification.",
            ],
        )

    with c2:
        st.dataframe(current_scenario_table(st.session_state.policy_posture_preset), width="stretch", hide_index=True)

    with st.expander("Advanced model settings", expanded=False):
        st.caption("Demo assumptions only. These settings do not represent final policy.")
        st.checkbox(
            "Only show low-legal-risk zones as pilot-review flags",
            key="require_legal_low_risk_for_pilot",
        )
        st.checkbox(
            "Require D5 fiscal data before pilot-review screening",
            key="require_fiscal_data_for_pilot",
        )
        st.checkbox(
            "Block cost-based support-review language when fiscal exposure is high",
            key="block_high_fiscal_exposure",
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
            "Apply minimum data-confidence gate across all treatment categories",
            key="strict_data_confidence_for_all",
        )
        st.checkbox(
            "Treat not-yet-validated developer compliance as blocker",
            key="treat_unknown_developer_compliance_as_blocker",
        )
        st.checkbox(
            "Prefer non-fiscal support path when additionality is weak or not yet validated",
            key="prefer_non_fiscal_when_additionality_uncertain",
        )
        st.checkbox(
            "Label wider screen as diagnostic only",
            key="diagnostic_only",
        )

    st.markdown("### Scenario Presets")
    st.dataframe(scenario_presets_table(), width="stretch", hide_index=True)

    st.markdown("### Selected-Zone Sensitivity")
    if demo_mode_active():
        case = current_demo_case(frames["recommendations"])
        selected_zone_id = case.get("zone_id") if case else frames["zones"]["zone_id"].iloc[0]
        st.info(f"Synthetic demo sensitivity is using: {case['label'] if case else 'selected demo case'}")
    else:
        zones = frames["zones"].copy()
        zone_lookup = zones[["zone_id", "zone_name", "province"]].drop_duplicates()
        zone_lookup["Display"] = zone_lookup.apply(
            lambda row: f"{row['zone_name']} - {row['province']}" if str(row.get("province", "")).strip() else str(row["zone_name"]),
            axis=1,
        )
        selected_display = st.selectbox("Selected zone", zone_lookup["Display"].tolist(), key="scenario_selected_zone")
        selected_zone_id = zone_lookup.loc[zone_lookup["Display"] == selected_display, "zone_id"].iloc[0]
    st.dataframe(
        scenario_sensitivity_table(frames, selected_zone_id, scenario_from_state()),
        width="stretch",
        hide_index=True,
    )

    st.markdown("### Sensitivity Examples")
    st.dataframe(scenario_examples_table(), width="stretch", hide_index=True)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def safe_file_token(value: object, default: str = "selected_zone") -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", display_value(value, default)).strip("_")
    return token or default


def export_metadata(summary: dict[str, Any], rec: pd.Series | None = None) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    run_id = datetime.now(timezone.utc).strftime(f"{APP_VERSION}-%Y%m%d%H%M%S")
    source = DATASET_BASIS_LABEL
    if rec is not None:
        source = source_reference(rec)
    return {
        "Dataset view": "Synthetic demo dataset",
        "Ruleset version": f"{APP_VERSION} / {APP_CONFIG['reason_codes_file'].stem}",
        "Rules posture": str(st.session_state.get("policy_posture_preset", "Broad diagnostic screen")),
        "Dataset basis": source,
        "Timestamp / run ID": f"{timestamp} / {run_id}",
    }


def memo_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if str(item).strip())


def selected_zone_memo(
    rec: pd.Series,
    reason_codes: dict[str, str],
    summary: dict[str, Any],
    *,
    plain_text: bool = False,
) -> str:
    calibration = dict(zip(calibration_output_table(rec)["Field"], calibration_output_table(rec)["Value"]))
    metadata = export_metadata(summary, rec)
    zone = display_value(rec.get("zone_name"), "Selected zone")
    title = f"{zone} \u2014 Prototype Screening Note"
    provisional = treatment_label(rec.get("provisional_treatment", rec.get("recommended_treatment")))
    treatment_class = display_value(calibration.get("Treatment class"), "More data required before treatment")
    reason_lines = [
        f"{code}: {display_reason_text(reason_codes.get(code, 'Unmapped reason code'))}"
        for code in split_reason_codes(rec.get("reason_codes"))
    ]
    core_gates = [
        "D4 legal review",
        "D5/FBR fiscal validation",
        "enterprise-level verification",
        "additionality / counterfactual assessment",
        "compliance validation",
    ]
    open_gates = core_gates + [
        gate for gate in split_pipe_text(rec.get("open_validation_gates", "")) if gate not in core_gates
    ]
    kpi_status = readiness_label(rec)
    next_action = display_action_text(rec.get("next_actions", "Human review required."))
    owner = display_value(rec.get("validator_owner"), "BOI / SEZA / FBR / Finance / legal / REMIT")
    basis = display_memo_text(rec.get("why", "Human review required before fiscal, legal, calibration, or pilot use."))
    metadata_lines = [f"- {key}: {value}" for key, value in metadata.items()]

    sections = [
        title,
        "",
        "Source / audit metadata",
        "\n".join(metadata_lines),
        "",
        "1. Provisional treatment",
        provisional,
        "",
        "2. Illustrative incentive treatment",
        treatment_class,
        "",
        "3. Calibration output \u2014 illustrative only",
        memo_bullets(
            [
                f"Possible instrument: {calibration.get('Possible instrument', 'To be determined after D5/D6 validation')}",
                f"Support intensity: {calibration.get('Support intensity', 'Not determined')}",
                f"Fiscal cap: {calibration.get('Fiscal cap', 'Pending D5 validation')}",
                f"Duration / sunset: {calibration.get('Duration / sunset', 'Not applicable')}",
                f"Conditions: {calibration.get('Conditions', 'D4 legal review; D5/FBR fiscal exposure validation')}",
            ]
        ),
        "",
        "4. Basis for treatment",
        basis,
        "",
        "5. Open validation gates",
        memo_bullets(open_gates),
        "",
        "6. Reason codes",
        memo_bullets(reason_lines),
        "",
        "7. Additionality and net-impact caveat",
        "Observed activity does not prove incentive effectiveness. Additionality and net fiscal/economic impact require separate validation.",
        "",
        "8. KPI assurance status",
        kpi_status,
        "",
        "9. Next required action",
        next_action,
        "",
        "10. Validator / owner",
        owner,
        "",
        "11. Use limitation",
        "This is a prototype screening output for discussion only. It is not a final legal, fiscal, tax, or incentive decision.",
        PUBLIC_LINK_WARNING,
        SOURCE_PERMISSION_WARNING if str(st.session_state.get("data_mode")) != "Synthetic demo data" else "",
    ]
    memo = "\n".join(sections)
    if plain_text:
        return memo.replace("\u2014", "-")
    return memo


def render_export(
    frames: dict[str, pd.DataFrame],
    summary: dict[str, Any],
    reason_codes: dict[str, str],
    display_recommendations: pd.DataFrame,
) -> None:
    st.markdown("### Export")
    st.caption("Generate policy-work-product style outputs for review, audit, email, or offline analysis.")

    recommendations = frames["recommendations"]
    if demo_mode_active():
        case = current_demo_case(recommendations)
        selected_zone_id = case.get("zone_id") if case else recommendations["zone_id"].iloc[0]
        selected_rec = recommendations[recommendations["zone_id"].astype(str) == str(selected_zone_id)].iloc[0]
        selected_rec = anonymized_demo_record(selected_rec, case)
        selected_file_source = case.get("key") if case else "demo_case"
        st.info(f"Synthetic demo memo export is using: {case['label'] if case else 'selected demo case'}")
    else:
        zone_lookup = recommendations[["zone_id", "zone_name", "province"]].drop_duplicates().copy()
        zone_lookup["Display"] = zone_lookup.apply(
            lambda row: f"{row['zone_name']} - {row['province']}" if str(row.get("province", "")).strip() else str(row["zone_name"]),
            axis=1,
        )
        selected_display = st.selectbox("Selected zone for memo and scenario export", zone_lookup["Display"].tolist())
        selected_zone_id = zone_lookup.loc[zone_lookup["Display"] == selected_display, "zone_id"].iloc[0]
        selected_rec = recommendations[recommendations["zone_id"].astype(str) == str(selected_zone_id)].iloc[0]
        selected_file_source = selected_rec["zone_id"]
    selected_file_token = safe_file_token(selected_file_source)

    st.markdown("### Work-Product Exports")
    export_display = demo_display_rows(display_recommendations, recommendations) if demo_mode_active() else display_recommendations
    triage_export = executive_table(export_display)
    validation_export = demo_scope_table(validation_display_table(frames), recommendations)
    scenario_export = scenario_sensitivity_table(frames, selected_zone_id, scenario_from_state())
    metadata = export_metadata(summary, selected_rec)

    with st.container(border=True):
        st.markdown("#### Source / Audit Metadata")
        st.dataframe(pd.DataFrame([metadata]), width="stretch", hide_index=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Export Executive Triage Table as CSV",
            data=dataframe_to_csv_bytes(triage_export),
            file_name="executive_triage_table.csv",
            mime="text/csv",
        )
    with c2:
        st.download_button(
            "Export Validation Flags as CSV",
            data=dataframe_to_csv_bytes(validation_export),
            file_name="validation_flags.csv",
            mime="text/csv",
        )
    with c3:
        st.download_button(
            "Export Scenario Comparison as CSV",
            data=dataframe_to_csv_bytes(scenario_export),
            file_name=f"scenario_comparison_{selected_file_token}.csv",
            mime="text/csv",
        )

    st.markdown("### Selected-Zone Memo")
    st.caption("Generate a concise screening note that can be reviewed before download.")
    if st.button("Generate selected-zone memo"):
        st.session_state.export_selected_zone_id = str(selected_zone_id)
        st.session_state.export_memo_markdown = selected_zone_memo(selected_rec, reason_codes, summary)
        st.session_state.export_memo_txt = selected_zone_memo(selected_rec, reason_codes, summary, plain_text=True)

    if st.session_state.get("export_selected_zone_id") == str(selected_zone_id) and st.session_state.get("export_memo_markdown"):
        memo_markdown = st.session_state.export_memo_markdown
        memo_txt = st.session_state.export_memo_txt
        st.markdown("#### Export Preview")
        with st.container(border=True):
            st.markdown(memo_markdown)
        m1, m2 = st.columns(2)
        with m1:
            st.download_button(
                "Export Selected-Zone Explanation as Markdown",
                data=memo_markdown.encode("utf-8"),
                file_name=f"{selected_file_token}_prototype_screening_note.md",
                mime="text/markdown",
            )
        with m2:
            st.download_button(
                "Export Selected-Zone Explanation as TXT",
                data=memo_txt.encode("utf-8"),
                file_name=f"{selected_file_token}_prototype_screening_note.txt",
                mime="text/plain",
            )
    else:
        st.info("Select a zone and click Generate selected-zone memo to preview the note before downloading.")

    st.markdown("### Export Previews")
    with st.expander("Executive triage table preview"):
        st.dataframe(triage_export, width="stretch", hide_index=True)
    with st.expander("Validation flags preview"):
        st.dataframe(validation_export, width="stretch", hide_index=True)
    with st.expander("Scenario comparison preview"):
        st.dataframe(scenario_export, width="stretch", hide_index=True)

    output_dir = ROOT / "outputs"
    export_files = [
        ("zone_triage_prototype.csv", "Download generated triage table"),
        ("recommendation_explanations.csv", "Download screening output explanations"),
        ("audit_flags.csv", "Download audit flags"),
        ("data_quality_issue_log.csv", "Download validation flags"),
        ("contradiction_log.csv", "Download cross-source/status conflicts"),
        ("data_confidence_scores.csv", "Download confidence scores"),
        ("activity_classification.csv", "Download activity classification"),
        ("field_completeness.csv", "Download field completeness"),
        ("summary.json", "Download summary JSON"),
        ("sez_calibration_demo_outputs.xlsx", "Download Excel output package"),
    ]

    if not demo_mode_active():
        with st.expander("Full generated output package"):
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
reason_codes = load_reason_codes(APP_CONFIG["reason_codes_file"])
recommendations = frames["recommendations"]
display_recommendations = recommendation_view(recommendations)

page = render_header(recommendations, summary)

if page == "Executive Triage":
    render_executive_view(frames, summary, display_recommendations)
elif page == "Case Review":
    render_case_review(frames, reason_codes, display_recommendations)
elif page == "Data Confidence":
    render_data_confidence_mvp(frames, summary)
elif page == "Export":
    render_export_memo(frames, summary, reason_codes, display_recommendations)
elif page == "About / Limitations":
    render_about_limitations(summary)
elif page == "Scenario Settings" and SHOW_ADVANCED_SCENARIOS:
    render_scenario_settings(frames, summary)

render_footer()
