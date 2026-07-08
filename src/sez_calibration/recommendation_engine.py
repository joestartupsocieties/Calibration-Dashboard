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
    "enterprise_compliance_status",
    "activity_category",
    "fiscal_exposure_level",
    "fiscal_data_status",
    "additionality_confidence",
    "incentive_effectiveness_confidence",
    "net_fiscal_economic_impact",
    "fiscal_exposure_status",
    "legal_status",
    "compliance_status",
    "provisional_treatment",
    "recommended_treatment",
    "illustrative_support_treatment",
    "illustrative_instrument_options",
    "why",
    "blocking_validation_requirements",
    "data_gaps",
    "validator_owner",
    "possible_screen_candidate_flag",
    "hard_gates_triggered",
    "reason_codes",
    "next_actions",
    "required_data_action",
    "required_legal_action",
    "required_fbr_action",
    "human_review_status",
    "human_override_flag",
    "override_reason",
]

PROVISIONAL_TREATMENTS = {
    "more_data": "More data required",
    "legal": "Legal review required",
    "fiscal": "Fiscal/FBR verification required",
    "sanction": "Sanction / withdrawal review",
    "transition": "Temporary grandfathering / transition review",
    "non_fiscal": "Non-fiscal support only",
    "limited_cost": "Limited cost-based support review",
    "pilot": "Potential pilot-review candidate",
    "phase_out": "Phase-out / no new support",
}
SUPPORT_TREATMENTS = {
    "none": "No new fiscal support",
    "non_fiscal": "Non-fiscal support only",
    "limited_cost": "Limited cost-based support review",
    "grandfathering": "Temporary grandfathering subject to legal review",
    "transition": "Transition / early-adoption review",
    "pilot": "Pilot-review only",
    "sanction": "Sanction / withdrawal review",
    "more_data": "More data required before support decision",
}
INSTRUMENT_OPTIONS = {
    "none": "None",
    "capex": "CAPEX expensing review",
    "training": "Training deduction review",
    "rd": "R&D deduction review",
    "infrastructure": "Infrastructure-linked non-fiscal support",
    "facilitation": "Regulatory / one-window / utilities facilitation only",
    "grandfathering": "Grandfathering / transition treatment subject to legal review",
}
BAND_RANK = {"do_not_use": 0, "low": 1, "medium": 2, "high": 3}


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
        rows.append(_recommend(row, issue_df if issue_df is not None else pd.DataFrame(), scenario))
    return pd.DataFrame(rows, columns=RECOMMENDATION_COLUMNS)


def apply_legal_gate(record: pd.Series | dict[str, Any]) -> list[dict[str, object]]:
    legal_risk = _record_text(record, "legal_risk_level") or "unknown"
    legal_review_required = to_bool(_record_value(record, "legal_review_required"))
    gates: list[dict[str, object]] = []
    if legal_risk == "high":
        gates.append(
            _gate(
                "high_legal_risk",
                "High legal or contractual risk blocks treatment screening until D4 review is complete.",
                ["R01", "R14", "R17"],
                "Legal team / BOI / SEZA",
            )
        )
    elif legal_risk in {"", "unknown"} or legal_review_required:
        gates.append(
            _gate(
                "legal_review_required",
                "Legal classification is unknown or placeholder-based; D4 legal review is required.",
                ["R14", "R02", "R20", "R17"],
                "Legal team / BOI / SEZA",
            )
        )
    return gates


def apply_compliance_gate(record: pd.Series | dict[str, Any]) -> list[dict[str, object]]:
    developer = _record_text(record, "developer_compliance_status") or "unknown"
    enterprise = _record_text(record, "enterprise_compliance_status") or "unknown"
    gates: list[dict[str, object]] = []
    if "non_compliant" in {developer, enterprise}:
        gates.append(
            _gate(
                "compliance_non_compliant",
                "Developer or enterprise compliance concern requires sanction / withdrawal review.",
                ["R03", "R21", "R17"],
                "SEZA / legal team",
            )
        )
    elif developer in {"unknown", "partial", "partially_compliant", ""} or enterprise in {
        "unknown",
        "partial",
        "partially_compliant",
        "",
    }:
        gates.append(
            _gate(
                "compliance_validation_required",
                "Developer or enterprise compliance is not validated.",
                ["R03", "R21", "R22", "R17"],
                "SEZA / BOI",
                blocking=bool(_record_value(record, "_treat_unknown_compliance_as_blocker")),
            )
        )
    return gates


def apply_data_confidence_gate(record: pd.Series | dict[str, Any]) -> list[dict[str, object]]:
    band = _record_text(record, "data_confidence_band") or "do_not_use"
    gates: list[dict[str, object]] = []
    if band in {"low", "do_not_use"}:
        gates.append(
            _gate(
                "low_data_confidence",
                "Data confidence is too low for fiscal or calibration use.",
                ["R08", "R19", "R17"],
                "BOI / SEZA data team",
            )
        )
    return gates


def apply_fiscal_gate(record: pd.Series | dict[str, Any]) -> list[dict[str, object]]:
    exposure = _record_text(record, "fiscal_exposure_level") or "unknown"
    status = _record_text(record, "fiscal_data_status") or "missing"
    gates: list[dict[str, object]] = []
    if exposure in {"", "unknown", "missing"} or status in {"", "missing", "unknown", "placeholder"}:
        gates.append(
            _gate(
                "fiscal_exposure_missing",
                "Fiscal exposure is missing or placeholder-based; D5/FBR/customs verification is required.",
                ["R09", "R13", "R17"],
                "FBR / Finance / D5 team",
            )
        )
    elif exposure == "high":
        gates.append(
            _gate(
                "high_fiscal_exposure",
                "Reported fiscal exposure is high and requires D5/FBR validation before treatment screening.",
                ["R10", "R13", "R17"],
                "FBR / Finance / D5 team",
            )
        )
    return gates


def apply_additionality_gate(record: pd.Series | dict[str, Any]) -> list[dict[str, object]]:
    additionality = _record_text(record, "additionality_confidence") or infer_additionality_confidence(record).lower()
    activity = _normalized_activity(record)
    gates: list[dict[str, object]] = []
    if additionality in {"", "unknown"}:
        gates.append(
            _gate(
                "additionality_uncertain",
                "Additionality is not validated; reported activity is not proof that incentives caused the activity.",
                ["R11", "R17"],
                "REMIT / Finance / BOI",
                blocking=False,
            )
        )
    elif activity in {"vacant_or_speculative", "allotted_but_inactive"}:
        gates.append(
            _gate(
                "weak_incentive_effectiveness_evidence",
                "Vacancy, idle land, or allotment-only movement is weak evidence of incentive effectiveness.",
                ["R06", "R07", "R11", "R16", "R17"],
                "REMIT / BOI / SEZA",
                blocking=False,
            )
        )
    return gates


def generate_reason_codes(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> list[str]:
    codes: list[str] = []
    for gate in gates:
        codes.extend(str(code) for code in gate.get("codes", []))

    activity = _normalized_activity(record)
    if activity == "operating_productive":
        codes.append("R04")
    elif activity == "moving_toward_production":
        codes.append("R05")
    elif activity == "allotted_but_inactive":
        codes.append("R06")
    elif activity == "vacant_or_speculative":
        codes.append("R07")

    if _has_infrastructure_constraint(record):
        codes.append("R12")
    if _record_value(record, "_source_scope_issue"):
        codes.append("R18")
    codes.append("R19")
    if _record_text(record, "enterprise_compliance_status") in {"", "unknown"}:
        codes.append("R22")
    if _legal_or_fiscal_unresolved(gates):
        codes.extend(["R14", "R13"])
    if activity == "operating_productive" and not _has_blocking_gate(gates):
        codes.append("R15")
    codes.append("R17")
    return _unique(codes)


def generate_provisional_treatment(record: pd.Series | dict[str, Any], gates: list[dict[str, object]], score: float) -> str:
    activity = _normalized_activity(record)
    if _has_gate(gates, "low_data_confidence"):
        return PROVISIONAL_TREATMENTS["more_data"]
    if _has_gate(gates, "compliance_non_compliant"):
        return PROVISIONAL_TREATMENTS["sanction"]
    if _has_gate(gates, "high_legal_risk"):
        return PROVISIONAL_TREATMENTS["legal"]
    if _has_gate(gates, "scenario_legal_low_risk_required"):
        return PROVISIONAL_TREATMENTS["legal"]
    if _has_gate(gates, "scenario_fiscal_data_required"):
        return PROVISIONAL_TREATMENTS["fiscal"]
    if _has_gate(gates, "scenario_minimum_confidence_band") or _has_gate(gates, "scenario_construction_excluded"):
        return PROVISIONAL_TREATMENTS["more_data"]
    if _has_gate(gates, "scenario_unknown_developer_compliance_blocker"):
        return PROVISIONAL_TREATMENTS["more_data"]
    if activity == "vacant_or_speculative":
        return PROVISIONAL_TREATMENTS["phase_out"]
    if activity == "allotted_but_inactive":
        return PROVISIONAL_TREATMENTS["non_fiscal"]
    if activity == "moving_toward_production":
        return PROVISIONAL_TREATMENTS["transition"]
    if activity == "operating_productive":
        if _support_ready(record, gates, score):
            return PROVISIONAL_TREATMENTS["limited_cost"]
        return PROVISIONAL_TREATMENTS["pilot"]
    if activity == "unclear":
        return PROVISIONAL_TREATMENTS["more_data"]
    if _has_gate(gates, "legal_review_required"):
        return PROVISIONAL_TREATMENTS["legal"]
    if _has_gate(gates, "fiscal_exposure_missing") or _has_gate(gates, "high_fiscal_exposure"):
        return PROVISIONAL_TREATMENTS["fiscal"]
    return PROVISIONAL_TREATMENTS["more_data"]


def generate_illustrative_support_treatment(
    record: pd.Series | dict[str, Any], gates: list[dict[str, object]], score: float
) -> str:
    treatment = generate_provisional_treatment(record, gates, score)
    activity = _normalized_activity(record)
    if treatment == PROVISIONAL_TREATMENTS["more_data"]:
        return SUPPORT_TREATMENTS["more_data"]
    if treatment == PROVISIONAL_TREATMENTS["sanction"]:
        return SUPPORT_TREATMENTS["sanction"]
    if treatment == PROVISIONAL_TREATMENTS["legal"]:
        return SUPPORT_TREATMENTS["grandfathering"]
    if treatment == PROVISIONAL_TREATMENTS["phase_out"]:
        return SUPPORT_TREATMENTS["none"]
    if treatment == PROVISIONAL_TREATMENTS["non_fiscal"]:
        return SUPPORT_TREATMENTS["non_fiscal"]
    if treatment == PROVISIONAL_TREATMENTS["transition"] or activity == "moving_toward_production":
        return SUPPORT_TREATMENTS["transition"]
    if treatment == PROVISIONAL_TREATMENTS["limited_cost"] and not _legal_or_fiscal_unresolved(gates):
        return SUPPORT_TREATMENTS["limited_cost"]
    return SUPPORT_TREATMENTS["pilot"]


def generate_next_action(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> str:
    if _has_gate(gates, "low_data_confidence"):
        return "BOI/SEZA data team should resolve validation flags and source-row verification before fiscal or calibration use."
    if _has_gate(gates, "compliance_non_compliant"):
        return "SEZA and the legal team should run sanction / withdrawal review before any support discussion."
    if _has_gate(gates, "high_legal_risk") or _has_gate(gates, "legal_review_required"):
        return "D4 legal team should validate legal classification, contractual constraints, sunset issues, and grandfathering exposure."
    if _has_gate(gates, "fiscal_exposure_missing") or _has_gate(gates, "high_fiscal_exposure"):
        return "FBR/Finance/D5 team should validate fiscal exposure, customs data, and any zone-wise cost-risk flags."
    if _has_gate(gates, "additionality_uncertain"):
        return "REMIT/Finance should test additionality and net fiscal/economic impact before any treatment category is used."
    return "Prepare a validation pack for BOI, SEZA, FBR, Finance, legal team, and REMIT review."


def get_validator_owner(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> str:
    owners: list[str] = []
    for gate in gates:
        owners.extend(str(part).strip() for part in str(gate.get("owner", "")).replace("/", ";").split(";") if part.strip())
    if not owners:
        owners = ["BOI", "REMIT"]
    return " / ".join(_unique(owners))


def _recommend(row: pd.Series, issue_df: pd.DataFrame, scenario: dict[str, Any]) -> dict[str, object]:
    record = row.copy()
    record["_treat_unknown_compliance_as_blocker"] = to_bool(scenario.get("treat_unknown_developer_compliance_as_blocker"))
    record["_source_scope_issue"] = _has_source_scope_issue(row, issue_df)

    activity = _normalized_activity(record)
    score = to_float(row.get("data_confidence_score")) or 0.0
    band = _record_text(row, "data_confidence_band") or "do_not_use"
    fiscal_exposure = _record_text(row, "fiscal_exposure_level") or "unknown"
    fiscal_status = _record_text(row, "fiscal_data_status") or "missing"
    additionality = infer_additionality_confidence(record)
    record["additionality_confidence"] = additionality

    gates = (
        apply_data_confidence_gate(record)
        + apply_legal_gate(record)
        + apply_compliance_gate(record)
        + apply_fiscal_gate(record)
        + apply_additionality_gate(record)
        + _scenario_gates(record, scenario)
    )
    gates = _dedupe_gates(gates)
    codes = generate_reason_codes(record, gates)
    provisional = generate_provisional_treatment(record, gates, score)
    support = generate_illustrative_support_treatment(record, gates, score)
    instruments = generate_illustrative_instruments(record, gates, support)
    why = generate_why(record, provisional, support, gates)
    blocking = generate_blocking_requirements(gates)
    data_gaps = generate_data_gaps(record, gates)
    next_action = generate_next_action(record, gates)
    validator_owner = get_validator_owner(record, gates)
    legal_risk = _record_text(row, "legal_risk_level") or "unknown"
    developer_compliance = _record_text(row, "developer_compliance_status") or "unknown"
    enterprise_compliance = _record_text(row, "enterprise_compliance_status") or "unknown"

    return {
        "zone_id": row.get("zone_id"),
        "zone_name": row.get("zone_name"),
        "province": row.get("province"),
        "operational_status": row.get("operational_status"),
        "data_confidence_score": round(score, 4),
        "data_confidence_band": band,
        "legal_risk_level": legal_risk,
        "developer_compliance_status": developer_compliance,
        "enterprise_compliance_status": enterprise_compliance,
        "activity_category": activity,
        "fiscal_exposure_level": fiscal_exposure,
        "fiscal_data_status": fiscal_status,
        "additionality_confidence": additionality,
        "incentive_effectiveness_confidence": infer_incentive_effectiveness_confidence(record),
        "net_fiscal_economic_impact": infer_net_fiscal_economic_impact(record),
        "fiscal_exposure_status": fiscal_exposure_status(record),
        "legal_status": legal_status(record),
        "compliance_status": compliance_status(record),
        "provisional_treatment": provisional,
        "recommended_treatment": provisional,
        "illustrative_support_treatment": support,
        "illustrative_instrument_options": "; ".join(instruments),
        "why": why,
        "blocking_validation_requirements": " | ".join(blocking) if blocking else "None beyond standard human review.",
        "data_gaps": " | ".join(data_gaps) if data_gaps else "No additional data gaps identified by the prototype.",
        "validator_owner": validator_owner,
        "possible_screen_candidate_flag": _pilot_review_flag(provisional, gates),
        "hard_gates_triggered": "; ".join(gate["id"] for gate in gates if gate.get("blocking", True)) or "none",
        "reason_codes": "; ".join(codes),
        "next_actions": next_action,
        "required_data_action": _data_action(record, gates),
        "required_legal_action": _legal_action(record, gates),
        "required_fbr_action": _fbr_action(record, gates),
        "human_review_status": "Required",
        "human_override_flag": False,
        "override_reason": "",
    }


def infer_additionality_confidence(record: pd.Series | dict[str, Any]) -> str:
    value = clean_text(_record_value(record, "additionality_confidence"))
    if value:
        return _title_status(value, {"unknown": "Unknown", "low": "Low", "medium": "Medium", "high": "High"})
    activity = _normalized_activity(record)
    if activity in {"vacant_or_speculative", "allotted_but_inactive"}:
        return "Low"
    return "Unknown"


def infer_incentive_effectiveness_confidence(record: pd.Series | dict[str, Any]) -> str:
    value = clean_text(_record_value(record, "incentive_effectiveness_confidence"))
    if value:
        return _title_status(value, {"unknown": "Unknown", "weak": "Weak", "moderate": "Moderate", "strong": "Strong"})
    activity = _normalized_activity(record)
    if activity in {"vacant_or_speculative", "allotted_but_inactive"}:
        return "Weak"
    if activity == "operating_productive" and _record_text(record, "data_confidence_band") == "high":
        return "Moderate"
    return "Unknown"


def infer_net_fiscal_economic_impact(record: pd.Series | dict[str, Any]) -> str:
    value = clean_text(_record_value(record, "net_fiscal_economic_impact"))
    if value:
        return _title_status(value, {"unknown": "Unknown", "negative": "Negative", "mixed": "Mixed", "positive": "Positive"})
    return "Unknown"


def fiscal_exposure_status(record: pd.Series | dict[str, Any]) -> str:
    exposure = _record_text(record, "fiscal_exposure_level") or "unknown"
    status = _record_text(record, "fiscal_data_status") or "missing"
    if status in {"validated", "verified"}:
        return "Validated"
    if status == "preliminary":
        return "Preliminary"
    if exposure in {"unknown", "missing", ""} or status == "missing":
        return "Missing"
    return "Placeholder"


def legal_status(record: pd.Series | dict[str, Any]) -> str:
    risk = _record_text(record, "legal_risk_level") or "unknown"
    if risk == "high":
        return "High risk"
    if risk == "medium":
        return "Medium risk"
    if risk == "low":
        return "Low risk"
    return "Requires D4 review"


def compliance_status(record: pd.Series | dict[str, Any]) -> str:
    developer = _record_text(record, "developer_compliance_status") or "unknown"
    enterprise = _record_text(record, "enterprise_compliance_status") or "unknown"
    statuses = {developer, enterprise}
    if "non_compliant" in statuses:
        return "Non-compliant"
    if statuses <= {"compliant"}:
        return "Compliant"
    if statuses & {"partial", "partially_compliant"}:
        return "Partially compliant"
    if statuses <= {"unknown", ""}:
        return "Unknown"
    return "Requires validation"


def generate_illustrative_instruments(
    record: pd.Series | dict[str, Any], gates: list[dict[str, object]], support_treatment: str
) -> list[str]:
    activity = _normalized_activity(record)
    if support_treatment in {
        SUPPORT_TREATMENTS["none"],
        SUPPORT_TREATMENTS["sanction"],
        SUPPORT_TREATMENTS["more_data"],
    }:
        return [INSTRUMENT_OPTIONS["none"]]
    if support_treatment == SUPPORT_TREATMENTS["non_fiscal"]:
        return [INSTRUMENT_OPTIONS["facilitation"]]
    if support_treatment == SUPPORT_TREATMENTS["transition"]:
        return [INSTRUMENT_OPTIONS["grandfathering"], INSTRUMENT_OPTIONS["infrastructure"], INSTRUMENT_OPTIONS["facilitation"]]
    if support_treatment == SUPPORT_TREATMENTS["grandfathering"]:
        return [INSTRUMENT_OPTIONS["grandfathering"]]
    if support_treatment == SUPPORT_TREATMENTS["limited_cost"] and not _legal_or_fiscal_unresolved(gates):
        return [INSTRUMENT_OPTIONS["capex"], INSTRUMENT_OPTIONS["training"], INSTRUMENT_OPTIONS["rd"]]
    if activity == "operating_productive":
        return [INSTRUMENT_OPTIONS["capex"], INSTRUMENT_OPTIONS["training"], INSTRUMENT_OPTIONS["facilitation"]]
    return [INSTRUMENT_OPTIONS["facilitation"]]


def generate_why(
    record: pd.Series | dict[str, Any],
    provisional_treatment: str,
    support_treatment: str,
    gates: list[dict[str, object]],
) -> str:
    zone_name = clean_text(_record_value(record, "zone_name")) or "This zone"
    activity = _normalized_activity(record)
    confidence = _record_text(record, "data_confidence_band").replace("_", " ") or "unknown"
    activity_text = {
        "operating_productive": "reported data shows production activity",
        "moving_toward_production": "reported data shows construction-stage movement, not operating production",
        "allotted_but_inactive": "reported data shows allotment movement without productive-use evidence",
        "vacant_or_speculative": "reported data shows high vacant or idle land signals",
        "unclear": "the available record does not support a clear activity classification",
    }.get(activity, "the available record does not support a clear activity classification")
    gate_text = "; ".join(str(gate["label"]) for gate in gates[:3]) or "standard human review still applies"
    return (
        f"{zone_name} receives a provisional treatment of {provisional_treatment} because {activity_text} "
        f"and data confidence is {confidence}. The illustrative support treatment is {support_treatment}, "
        "subject to validation and not a final policy decision. "
        f"Key validation requirements are: {gate_text}."
    )


def generate_blocking_requirements(gates: list[dict[str, object]]) -> list[str]:
    requirements = [str(gate["label"]) for gate in gates if gate.get("blocking", True)]
    if not any("human review" in req.lower() for req in requirements):
        requirements.append("Human review is required before any legal, fiscal, tax, incentive, or policy decision.")
    return _unique(requirements)


def generate_data_gaps(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> list[str]:
    gaps: list[str] = []
    if _has_gate(gates, "low_data_confidence"):
        gaps.append("Low or unusable confidence score; source data needs repair.")
    if _has_gate(gates, "fiscal_exposure_missing"):
        gaps.append("Fiscal exposure, FBR, and customs data are missing or placeholder-based.")
    if _has_gate(gates, "legal_review_required") or _has_gate(gates, "high_legal_risk"):
        gaps.append("D4 legal classification, contractual position, and sunset/grandfathering status are unresolved.")
    if _has_gate(gates, "compliance_validation_required") or _has_gate(gates, "compliance_non_compliant"):
        gaps.append("Developer and enterprise compliance status requires validation.")
    if _has_gate(gates, "additionality_uncertain"):
        gaps.append("Additionality, incentive effectiveness, and net fiscal/economic impact are not validated.")
    if _record_value(record, "_source_scope_issue"):
        gaps.append("Coverage / definition mismatch remains unresolved.")
    gaps.append("Enterprise-level data and exact source rows require verification.")
    return _unique(gaps)


def _scenario_gates(record: pd.Series | dict[str, Any], scenario: dict[str, Any]) -> list[dict[str, object]]:
    gates: list[dict[str, object]] = []
    band = _record_text(record, "data_confidence_band") or "do_not_use"
    activity = _normalized_activity(record)
    legal_risk = _record_text(record, "legal_risk_level") or "unknown"
    fiscal_exposure = _record_text(record, "fiscal_exposure_level") or "unknown"
    fiscal_status = _record_text(record, "fiscal_data_status") or "missing"
    minimum_band = clean_text(scenario.get("minimum_data_confidence_band_for_pilot")).lower() or "medium"

    if _band_rank(band) < _band_rank(minimum_band) and activity in {"operating_productive", "moving_toward_production"}:
        gates.append(
            _gate(
                "scenario_minimum_confidence_band",
                "Advanced Model Settings require a higher confidence band before pilot-review screening.",
                ["R08", "R17"],
                "BOI / REMIT",
            )
        )
    if to_bool(scenario.get("require_legal_low_risk_for_pilot")) and legal_risk != "low" and activity in {
        "operating_productive",
        "moving_toward_production",
    }:
        gates.append(
            _gate(
                "scenario_legal_low_risk_required",
                "Advanced Model Settings require low legal risk before pilot-review screening.",
                ["R14", "R17"],
                "Legal team / BOI",
            )
        )
    if to_bool(scenario.get("require_fiscal_data_for_pilot")) and (
        fiscal_exposure in {"unknown", "missing", ""} or fiscal_status in {"missing", "unknown", ""}
    ):
        gates.append(
            _gate(
                "scenario_fiscal_data_required",
                "Advanced Model Settings require D5 fiscal data before pilot-review screening.",
                ["R09", "R13", "R17"],
                "FBR / Finance / D5 team",
            )
        )
    if scenario.get("include_construction_stage_transition_candidates") is False and activity == "moving_toward_production":
        gates.append(
            _gate(
                "scenario_construction_excluded",
                "Advanced Model Settings exclude construction-stage transition candidates.",
                ["R05", "R17"],
                "BOI / REMIT",
            )
        )
    if to_bool(scenario.get("treat_unknown_developer_compliance_as_blocker")) and (
        _record_text(record, "developer_compliance_status") in {"unknown", ""}
    ):
        gates.append(
            _gate(
                "scenario_unknown_developer_compliance_blocker",
                "Advanced Model Settings treat unknown developer compliance as a blocker.",
                ["R03", "R17", "R21"],
                "SEZA / BOI",
            )
        )
    return gates


def _support_ready(record: pd.Series | dict[str, Any], gates: list[dict[str, object]], score: float) -> bool:
    return (
        _normalized_activity(record) == "operating_productive"
        and score >= 0.8
        and _record_text(record, "legal_risk_level") in {"low", "medium"}
        and _record_text(record, "fiscal_exposure_level") not in {"", "unknown", "missing", "high"}
        and _record_text(record, "fiscal_data_status") in {"preliminary", "verified", "validated"}
        and compliance_status(record) == "Compliant"
        and infer_additionality_confidence(record) in {"Medium", "High"}
        and not _legal_or_fiscal_unresolved(gates)
    )


def _pilot_review_flag(provisional_treatment: str, gates: list[dict[str, object]]) -> bool:
    if provisional_treatment not in {PROVISIONAL_TREATMENTS["pilot"], PROVISIONAL_TREATMENTS["limited_cost"]}:
        return False
    blocking_ids = {
        "low_data_confidence",
        "high_legal_risk",
        "compliance_non_compliant",
        "scenario_minimum_confidence_band",
        "scenario_legal_low_risk_required",
        "scenario_fiscal_data_required",
        "scenario_construction_excluded",
        "scenario_unknown_developer_compliance_blocker",
    }
    return not any(gate["id"] in blocking_ids for gate in gates)


def _data_action(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> str:
    if _has_gate(gates, "low_data_confidence"):
        return "Resolve critical data gaps and cross-source/status conflicts before fiscal/calibration screening."
    return "Screening data usable for demo triage, but exact source-row verification remains required."


def _legal_action(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> str:
    if _has_gate(gates, "high_legal_risk"):
        return "Complete D4 legal review before any treatment category is used."
    if _has_gate(gates, "legal_review_required"):
        return "Replace placeholder legal fields with D4 legal classification and sunset/grandfathering assessment."
    return "Confirm no contractual, grandfathering, or legal sunset restriction before implementation."


def _fbr_action(record: pd.Series | dict[str, Any], gates: list[dict[str, object]]) -> str:
    if _has_gate(gates, "fiscal_exposure_missing") or _has_gate(gates, "high_fiscal_exposure"):
        return "Complete D5/FBR/customs fiscal exposure verification."
    return "Audit fiscal exposure, caps, and fiscal neutrality before any support review."


def _normalized_activity(record: pd.Series | dict[str, Any]) -> str:
    activity = _record_text(record, "activity_category") or "unclear"
    status = _record_text(record, "operational_status")
    if "under construction" in status and "under production" not in status and "production" not in status:
        return "moving_toward_production"
    return activity


def _has_infrastructure_constraint(record: pd.Series | dict[str, Any]) -> bool:
    fields = ["electricity_status", "gas_status", "water_status", "wastewater_status", "roads_status"]
    text = " ".join(_record_text(record, field) for field in fields)
    return any(token in text for token in ["not available", "partial", "work in progress", "pending", "required"])


def _has_source_scope_issue(row: pd.Series, issue_df: pd.DataFrame) -> bool:
    if "no 2026 colonization match" in clean_text(row.get("data_confidence")).lower():
        return True
    if issue_df.empty:
        return False
    global_scope = issue_df[issue_df["zone_id"].astype(str).isin(["ALL", "all"])]
    return not global_scope.empty


def _legal_or_fiscal_unresolved(gates: list[dict[str, object]]) -> bool:
    return any(
        gate["id"]
        in {
            "legal_review_required",
            "high_legal_risk",
            "fiscal_exposure_missing",
            "high_fiscal_exposure",
            "scenario_fiscal_data_required",
            "scenario_legal_low_risk_required",
        }
        for gate in gates
    )


def _has_blocking_gate(gates: list[dict[str, object]]) -> bool:
    return any(bool(gate.get("blocking", True)) for gate in gates)


def _has_gate(gates: list[dict[str, object]], gate_id: str) -> bool:
    return any(gate["id"] == gate_id for gate in gates)


def _gate(
    gate_id: str,
    label: str,
    codes: list[str],
    owner: str,
    *,
    blocking: bool = True,
) -> dict[str, object]:
    return {"id": gate_id, "label": label, "codes": codes, "owner": owner, "blocking": blocking}


def _dedupe_gates(gates: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for gate in gates:
        gate_id = str(gate["id"])
        if gate_id not in seen:
            out.append(gate)
            seen.add(gate_id)
    return out


def _unique(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _band_rank(band: str) -> int:
    return BAND_RANK.get(clean_text(band).lower(), 0)


def _record_value(record: pd.Series | dict[str, Any], key: str) -> Any:
    if isinstance(record, pd.Series):
        return record.get(key)
    return record.get(key)


def _record_text(record: pd.Series | dict[str, Any], key: str) -> str:
    return clean_text(_record_value(record, key)).lower()


def _title_status(value: str, mapping: dict[str, str]) -> str:
    key = clean_text(value).lower().replace(" ", "_")
    return mapping.get(key, clean_text(value).replace("_", " ").title() or "Unknown")
