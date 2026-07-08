from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sez_calibration.recommendation_engine import run_recommendation_engine


def base_frames(
    *,
    band: str = "medium",
    legal_risk: str = "unknown",
    developer_status: str = "unknown",
    enterprise_status: str = "unknown",
    activity: str = "operating_productive",
    fiscal_exposure: str = "unknown",
    fiscal_confidence: str = "missing",
    operational_status: str = "Under Production",
    additionality_confidence: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    zone = {"zone_id": "Z1", "zone_name": "Zone", "province": "Punjab", "operational_status": operational_status}
    if additionality_confidence is not None:
        zone["additionality_confidence"] = additionality_confidence
    zones = pd.DataFrame([zone])
    confidence = pd.DataFrame([{"zone_id": "Z1", "zone_name": "Zone", "data_confidence_score": 0.7, "data_confidence_band": band}])
    activity_df = pd.DataFrame([{"zone_id": "Z1", "zone_name": "Zone", "activity_category": activity}])
    legal = pd.DataFrame(
        [
            {
                "zone_id": "Z1",
                "zone_name": "Zone",
                "legal_risk_level": legal_risk,
                "developer_compliance_status": developer_status,
                "enterprise_compliance_status": enterprise_status,
                "legal_review_required": True,
            }
        ]
    )
    fiscal = pd.DataFrame(
        [
            {
                "zone_id": "Z1",
                "zone_name": "Zone",
                "fiscal_exposure_level": fiscal_exposure,
                "fiscal_data_status": fiscal_confidence,
            }
        ]
    )
    return zones, confidence, activity_df, legal, fiscal


def rec(scenario: dict[str, object] | None = None, **kwargs):
    return run_recommendation_engine(*base_frames(**kwargs), scenario=scenario).iloc[0]


def test_high_legal_risk_triggers_legal_review() -> None:
    result = rec(legal_risk="high")
    assert result["recommended_treatment"] == "Legal review required"
    assert result["illustrative_support_treatment"] == "Temporary grandfathering subject to legal review"
    assert "high_legal_risk" in result["hard_gates_triggered"]
    assert "R01" in result["reason_codes"]


def test_low_data_confidence_triggers_more_data_required() -> None:
    result = rec(band="do_not_use")
    assert result["recommended_treatment"] == "More data required"
    assert result["illustrative_support_treatment"] == "More data required before support decision"
    assert "low_data_confidence" in result["hard_gates_triggered"]
    assert "R08" in result["reason_codes"]


def test_non_compliant_developer_triggers_sanction_cure() -> None:
    result = rec(developer_status="non_compliant")
    assert result["recommended_treatment"] == "Sanction / withdrawal review"
    assert result["illustrative_support_treatment"] == "Sanction / withdrawal review"
    assert "compliance_non_compliant" in result["hard_gates_triggered"]
    assert "R03" in result["reason_codes"]
    assert "R21" in result["reason_codes"]


def test_productive_missing_fiscal_does_not_produce_final_eligibility() -> None:
    result = rec(activity="operating_productive", fiscal_exposure="unknown", fiscal_confidence="missing")
    assert "final" not in result["recommended_treatment"].lower()
    assert result["recommended_treatment"] == "Potential pilot-review candidate"
    assert result["illustrative_support_treatment"] == "Pilot-review only"
    assert result["fiscal_exposure_status"] == "Missing"
    assert result["additionality_confidence"] == "Unknown"
    assert "fiscal_exposure_missing" in result["hard_gates_triggered"]
    assert "R09" in result["reason_codes"]
    assert "R11" in result["reason_codes"]
    assert result["human_review_status"] == "Required"


def test_vacant_activity_triggers_no_new_fiscal_support() -> None:
    result = rec(activity="vacant_or_speculative")
    assert result["recommended_treatment"] == "Phase-out / no new support"
    assert result["illustrative_support_treatment"] == "No new fiscal support"
    assert "R07" in result["reason_codes"]


def test_allotted_inactive_triggers_non_fiscal_facilitation() -> None:
    result = rec(activity="allotted_but_inactive")
    assert result["recommended_treatment"] == "Non-fiscal support only"
    assert result["illustrative_support_treatment"] == "Non-fiscal support only"
    assert "R06" in result["reason_codes"]


def test_construction_activity_triggers_transition_candidate() -> None:
    result = rec(activity="moving_toward_production")
    assert result["recommended_treatment"] == "Temporary grandfathering / transition review"
    assert result["illustrative_support_treatment"] == "Transition / early-adoption review"
    assert "R05" in result["reason_codes"]


def test_unclear_activity_triggers_human_review() -> None:
    result = rec(
        activity="unclear",
        legal_risk="low",
        developer_status="compliant",
        enterprise_status="compliant",
        fiscal_exposure="low",
        fiscal_confidence="verified",
    )
    assert result["recommended_treatment"] == "More data required"
    assert "R17" in result["reason_codes"]


def test_every_recommendation_has_reason_codes() -> None:
    result = rec()
    assert len([part for part in result["reason_codes"].split(";") if part.strip()]) >= 2


def test_every_recommendation_has_next_actions_and_human_review() -> None:
    result = rec()
    assert result["next_actions"]
    assert result["human_review_status"] == "Required"
    assert result["provisional_treatment"]
    assert result["illustrative_support_treatment"]
    assert result["blocking_validation_requirements"]
    assert result["data_gaps"]
    assert result["validator_owner"]


def test_low_legal_risk_setting_blocks_non_low_pilot_candidate() -> None:
    result = rec(
        band="high",
        legal_risk="medium",
        developer_status="compliant",
        fiscal_exposure="low",
        fiscal_confidence="verified",
        scenario={"require_legal_low_risk_for_pilot": True},
    )
    assert not bool(result["possible_screen_candidate_flag"])
    assert "scenario_legal_low_risk_required" in result["hard_gates_triggered"]
    assert result["recommended_treatment"] == "Legal review required"


def test_d5_fiscal_setting_blocks_missing_fiscal_candidate() -> None:
    result = rec(
        band="high",
        legal_risk="low",
        developer_status="compliant",
        fiscal_exposure="unknown",
        fiscal_confidence="missing",
        scenario={"require_fiscal_data_for_pilot": True},
    )
    assert not bool(result["possible_screen_candidate_flag"])
    assert "scenario_fiscal_data_required" in result["hard_gates_triggered"]
    assert result["recommended_treatment"] == "Fiscal/FBR verification required"


def test_minimum_high_confidence_setting_blocks_medium_candidate() -> None:
    result = rec(
        band="medium",
        legal_risk="low",
        developer_status="compliant",
        fiscal_exposure="low",
        fiscal_confidence="verified",
        scenario={"minimum_data_confidence_band_for_pilot": "high"},
    )
    assert not bool(result["possible_screen_candidate_flag"])
    assert "scenario_minimum_confidence_band" in result["hard_gates_triggered"]
    assert result["recommended_treatment"] == "More data required"


def test_construction_toggle_excludes_transition_candidates() -> None:
    result = rec(
        band="high",
        legal_risk="low",
        developer_status="compliant",
        activity="moving_toward_production",
        scenario={"include_construction_stage_transition_candidates": False},
    )
    assert result["recommended_treatment"] == "More data required"
    assert "scenario_construction_excluded" in result["hard_gates_triggered"]


def test_unknown_developer_compliance_setting_blocks_candidate() -> None:
    result = rec(
        band="high",
        legal_risk="low",
        developer_status="unknown",
        fiscal_exposure="low",
        fiscal_confidence="verified",
        scenario={"treat_unknown_developer_compliance_as_blocker": True},
    )
    assert not bool(result["possible_screen_candidate_flag"])
    assert "scenario_unknown_developer_compliance_blocker" in result["hard_gates_triggered"]
    assert result["recommended_treatment"] == "More data required"


def test_under_construction_status_is_not_operating_productive() -> None:
    result = rec(
        band="high",
        legal_risk="low",
        developer_status="compliant",
        enterprise_status="compliant",
        fiscal_exposure="low",
        fiscal_confidence="verified",
        activity="operating_productive",
        operational_status="Under Construction",
    )
    assert result["activity_category"] == "moving_toward_production"
    assert result["recommended_treatment"] == "Temporary grandfathering / transition review"
