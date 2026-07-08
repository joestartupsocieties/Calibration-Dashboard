from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .utils import clean_text, load_yaml_mapping, to_bool, to_float


RECOMMENDATION_COLUMNS = [
    "zone_id",
    "zone_name",
    "province",
    "operational_status",
    "data_confidence_score",
    "data_confidence_band",
    "legal_risk_level",
    "developer_compliance_status",
    "activity_category",
    "fiscal_exposure_level",
    "recommended_treatment",
    "pilot_eligible_flag",
    "hard_gates_triggered",
    "reason_codes",
    "required_data_action",
    "required_legal_action",
    "required_fbr_action",
    "human_review_status",
    "human_override_flag",
    "override_reason",
]

LEGAL_FISCAL_REVIEW_CLAUSE = "subject to D4 legal review and D5 fiscal verification"
PHASE_OUT_CLAUSE = "temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035"


def load_reason_codes(path: Path) -> dict[str, str]:
    data = load_yaml_mapping(path)
    return {str(k): str(v) for k, v in data.items()}


def run_recommendation_engine(
    zone_df: pd.DataFrame,
    confidence_df: pd.DataFrame,
    activity_df: pd.DataFrame,
    legal_df: pd.DataFrame,
    fiscal_df: pd.DataFrame,
    issue_df: pd.DataFrame | None = None,
    scenario: dict[str, Any] | None = None,
) -> pd.DataFrame:
    scenario = scenario or {}
    merged = zone_df.merge(confidence_df, on=["zone_id", "zone_name"], how="left")
    merged = merged.merge(activity_df, on=["zone_id", "zone_name"], how="left")
    merged = merged.merge(legal_df, on=["zone_id", "zone_name"], how="left")
    merged = merged.merge(fiscal_df, on=["zone_id", "zone_name"], how="left")

    rows: list[dict[str, object]] = []
    for _, row in merged.iterrows():
        result = _recommend(row, issue_df if issue_df is not None else pd.DataFrame(), scenario)
        rows.append(result)
    return pd.DataFrame(rows, columns=RECOMMENDATION_COLUMNS)


def _recommend(row: pd.Series, issue_df: pd.DataFrame, scenario: dict[str, Any]) -> dict[str, object]:
    band = clean_text(row.get("data_confidence_band")).lower() or "do_not_use"
    score = to_float(row.get("data_confidence_score")) or 0.0
    legal_risk = clean_text(row.get("legal_risk_level")).lower() or "unknown"
    developer_compliance = clean_text(row.get("developer_compliance_status")).lower() or "unknown"
    activity = clean_text(row.get("activity_category")).lower() or "unclear"
    fiscal_exposure = clean_text(row.get("fiscal_exposure_level")).lower() or "unknown"
    fiscal_confidence = clean_text(row.get("fiscal_data_status")).lower() or "missing"

    codes: list[str] = []
    gates: list[str] = []
    treatment = "Human review required"
    pilot = False

    if band == "do_not_use":
        treatment = "More data required before decision"
        gates.append("do_not_use_data_confidence")
        codes.extend(["R08", "R12"])
    elif legal_risk == "high":
        treatment = "Legal review required before any incentive treatment"
        gates.append("high_legal_risk")
        codes.extend(["R01", "R02", "R12"])
    elif developer_compliance == "non_compliant":
        treatment = f"Sanction/cure review before any support; {LEGAL_FISCAL_REVIEW_CLAUSE}"
        gates.append("developer_non_compliant")
        codes.extend(["R03", "R15", "R12"])
    elif activity == "vacant_or_speculative":
        treatment = f"No new fiscal support; enforcement or land-use review; {LEGAL_FISCAL_REVIEW_CLAUSE}"
        gates.append("vacant_or_speculative_activity")
        codes.extend(["R07", "R13", "R15"])
    elif activity == "allotted_but_inactive":
        treatment = f"No new fiscal support; non-fiscal facilitation or cure plan only; {LEGAL_FISCAL_REVIEW_CLAUSE}"
        gates.append("allotted_but_inactive_activity")
        codes.extend(["R06", "R13", "R14"])
    elif activity == "moving_toward_production":
        treatment = f"Possible transition screen candidate; {LEGAL_FISCAL_REVIEW_CLAUSE}"
        pilot = band == "high" and legal_risk in {"low", "medium"}
        codes.extend(["R05", "R09", "R16", "R17"])
    elif activity == "operating_productive":
        if fiscal_exposure == "unknown" or fiscal_confidence == "missing":
            treatment = f"Possible pilot screen candidate; {LEGAL_FISCAL_REVIEW_CLAUSE}"
            pilot = band in {"medium", "high"} and legal_risk != "high"
            codes.extend(["R04", "R09", "R10", "R16", "R17"])
        else:
            treatment = f"Possible cost-based support screen candidate; {LEGAL_FISCAL_REVIEW_CLAUSE}; {PHASE_OUT_CLAUSE}"
            pilot = band in {"medium", "high"} and legal_risk in {"low", "medium"}
            codes.extend(["R04", "R10", "R16", "R17"])
    else:
        codes.extend(["R12", "R08" if band in {"low", "do_not_use"} else "R17"])

    if clean_text(row.get("legal_review_required")).lower() in {"true", "1", "yes"} or legal_risk == "unknown":
        codes.append("R01")
    if developer_compliance in {"unknown", "partial"}:
        codes.append("R03")
    if fiscal_exposure == "unknown" or fiscal_confidence == "missing":
        codes.append("R09")
    if _has_infrastructure_constraint(row):
        codes.append("R11")
    if _has_source_scope_issue(row, issue_df):
        codes.append("R18")

    threshold = to_float(scenario.get("data_confidence_threshold"))
    if threshold is not None and score < threshold:
        pilot = False
        gates.append("scenario_confidence_threshold")
        codes.extend(["R08", "R12"])
    if to_bool(scenario.get("require_legal_low_risk_for_pilot")) and legal_risk != "low":
        pilot = False
        if activity in {"operating_productive", "moving_toward_production"}:
            gates.append("scenario_legal_low_risk_required")
            codes.append("R01")
    if to_bool(scenario.get("require_fiscal_data_for_pilot")) and (fiscal_exposure == "unknown" or fiscal_confidence == "missing"):
        pilot = False
        if activity in {"operating_productive", "moving_toward_production"}:
            gates.append("scenario_fiscal_data_required")
            codes.append("R09")
    if scenario.get("include_construction_stage_transition_candidates") is False and activity == "moving_toward_production":
        treatment = "Construction-stage transition candidates excluded by scenario controls"
        pilot = False
        gates.append("scenario_construction_excluded")

    codes = _unique(codes)
    if len(codes) < 2:
        codes = _unique(codes + ["R12", "R17"])

    return {
        "zone_id": row.get("zone_id"),
        "zone_name": row.get("zone_name"),
        "province": row.get("province"),
        "operational_status": row.get("operational_status"),
        "data_confidence_score": round(score, 4),
        "data_confidence_band": band,
        "legal_risk_level": legal_risk,
        "developer_compliance_status": developer_compliance,
        "activity_category": activity,
        "fiscal_exposure_level": fiscal_exposure,
        "recommended_treatment": treatment,
        "pilot_eligible_flag": bool(pilot),
        "hard_gates_triggered": "; ".join(_unique(gates)) if gates else "none",
        "reason_codes": "; ".join(codes),
        "required_data_action": _data_action(band, gates),
        "required_legal_action": _legal_action(legal_risk, row),
        "required_fbr_action": _fbr_action(fiscal_exposure, fiscal_confidence),
        "human_review_status": "Required",
        "human_override_flag": False,
        "override_reason": "",
    }


def _unique(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _has_infrastructure_constraint(row: pd.Series) -> bool:
    fields = ["electricity_status", "gas_status", "water_status", "wastewater_status", "roads_status"]
    text = " ".join(clean_text(row.get(field)).lower() for field in fields)
    return any(token in text for token in ["not available", "partial", "work in progress", "pending", "required"])


def _has_source_scope_issue(row: pd.Series, issue_df: pd.DataFrame) -> bool:
    if "no 2026 colonization match" in clean_text(row.get("data_confidence")).lower():
        return True
    if issue_df.empty:
        return False
    global_scope = issue_df[issue_df["zone_id"].astype(str).isin(["ALL", "all"])]
    return not global_scope.empty


def _data_action(band: str, gates: list[str]) -> str:
    if band == "do_not_use" or "scenario_confidence_threshold" in gates:
        return "Resolve critical data gaps and contradictions before policy screening."
    if band == "low":
        return "Use only for preliminary screening; request missing critical fields."
    return "Screening data usable for demo triage, but exact row-level verification remains required."


def _legal_action(legal_risk: str, row: pd.Series) -> str:
    if legal_risk == "high":
        return "Complete D4 legal review before any treatment recommendation."
    if legal_risk in {"unknown", ""} or to_bool(row.get("legal_review_required")):
        return "Replace placeholder legal fields with D4 legal classification."
    return "Confirm no contractual or grandfathering restriction before implementation."


def _fbr_action(fiscal_exposure: str, fiscal_confidence: str) -> str:
    if fiscal_exposure == "unknown" or fiscal_confidence == "missing":
        return "Complete D5/FBR/customs fiscal exposure verification."
    return "Audit fiscal exposure, caps, and fiscal neutrality before support."
