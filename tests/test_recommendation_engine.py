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
    activity: str = "operating_productive",
    fiscal_exposure: str = "unknown",
    fiscal_confidence: str = "missing",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    zones = pd.DataFrame([{"zone_id": "Z1", "zone_name": "Zone", "province": "Punjab", "operational_status": "Under Production"}])
    confidence = pd.DataFrame([{"zone_id": "Z1", "zone_name": "Zone", "data_confidence_score": 0.7, "data_confidence_band": band}])
    activity_df = pd.DataFrame([{"zone_id": "Z1", "zone_name": "Zone", "activity_category": activity}])
    legal = pd.DataFrame(
        [
            {
                "zone_id": "Z1",
                "zone_name": "Zone",
                "legal_risk_level": legal_risk,
                "developer_compliance_status": developer_status,
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
    assert result["recommended_treatment"] == "Legal review required before any incentive treatment"
    assert "R01" in result["reason_codes"]


def test_low_data_confidence_triggers_more_data_required() -> None:
    result = rec(band="do_not_use")
    assert result["recommended_treatment"] == "More data required before decision"
    assert "R08" in result["reason_codes"]


def test_non_compliant_developer_triggers_sanction_cure() -> None:
    result = rec(developer_status="non_compliant")
    assert result["recommended_treatment"].startswith("Sanction/cure review before support")
    assert "subject to D4 legal review and D5 fiscal verification" in result["recommended_treatment"]
    assert "all SEZ fiscal incentives phase out by 30 June 2035" in result["recommended_treatment"]
    assert "R15" in result["reason_codes"]


def test_productive_missing_fiscal_does_not_produce_final_eligibility() -> None:
    result = rec(activity="operating_productive", fiscal_exposure="unknown", fiscal_confidence="missing")
    assert "final" not in result["recommended_treatment"].lower()
    assert result["recommended_treatment"].startswith("Possible pilot screen candidate pending D4 legal review and D5 fiscal verification")
    assert "all SEZ fiscal incentives phase out by 30 June 2035" in result["recommended_treatment"]
    assert "Subject to D4 legal review and D5 fiscal verification." in result["next_actions"]


def test_vacant_activity_triggers_no_new_fiscal_support() -> None:
    result = rec(activity="vacant_or_speculative")
    assert result["recommended_treatment"].startswith("No new fiscal support; enforcement or land-use review")
    assert "subject to D4 legal review and D5 fiscal verification" in result["recommended_treatment"]
    assert "R07" in result["reason_codes"]


def test_allotted_inactive_triggers_non_fiscal_facilitation() -> None:
    result = rec(activity="allotted_but_inactive")
    assert result["recommended_treatment"].startswith("No new fiscal support; non-fiscal facilitation or cure plan only")
    assert "all SEZ fiscal incentives phase out by 30 June 2035" in result["recommended_treatment"]
    assert "R06" in result["reason_codes"]


def test_construction_activity_triggers_transition_candidate() -> None:
    result = rec(activity="moving_toward_production")
    assert result["recommended_treatment"].startswith("Possible transition candidate; subject to D4 legal review and D5 fiscal verification")
    assert "R05" in result["reason_codes"]


def test_unclear_activity_triggers_human_review() -> None:
    result = rec(activity="unclear")
    assert result["recommended_treatment"] == "Human review required"
    assert "R12" in result["reason_codes"]


def test_every_recommendation_has_reason_codes() -> None:
    result = rec()
    assert len([part for part in result["reason_codes"].split(";") if part.strip()]) >= 2


def test_every_recommendation_has_next_actions_and_human_review() -> None:
    result = rec()
    assert result["next_actions"]
    assert result["human_review_status"] == "Required"


def test_low_legal_risk_setting_blocks_non_low_pilot_candidate() -> None:
    result = rec(
        band="high",
        legal_risk="medium",
        developer_status="compliant",
        fiscal_exposure="low",
        fiscal_confidence="verified",
        scenario={"require_legal_low_risk_for_pilot": True},
    )
    assert not bool(result["pilot_eligible_flag"])
    assert "scenario_legal_low_risk_required" in result["hard_gates_triggered"]


def test_d5_fiscal_setting_blocks_missing_fiscal_candidate() -> None:
    result = rec(
        band="high",
        legal_risk="low",
        developer_status="compliant",
        fiscal_exposure="unknown",
        fiscal_confidence="missing",
        scenario={"require_fiscal_data_for_pilot": True},
    )
    assert not bool(result["pilot_eligible_flag"])
    assert "scenario_fiscal_data_required" in result["hard_gates_triggered"]


def test_minimum_high_confidence_setting_blocks_medium_candidate() -> None:
    result = rec(
        band="medium",
        legal_risk="low",
        developer_status="compliant",
        fiscal_exposure="low",
        fiscal_confidence="verified",
        scenario={"minimum_data_confidence_band_for_pilot": "high"},
    )
    assert not bool(result["pilot_eligible_flag"])
    assert "scenario_minimum_confidence_band" in result["hard_gates_triggered"]


def test_construction_toggle_excludes_transition_candidates() -> None:
    result = rec(
        band="high",
        legal_risk="low",
        developer_status="compliant",
        activity="moving_toward_production",
        scenario={"include_construction_stage_transition_candidates": False},
    )
    assert result["recommended_treatment"] == "Human review required"
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
    assert not bool(result["pilot_eligible_flag"])
    assert "scenario_unknown_developer_compliance_blocker" in result["hard_gates_triggered"]
    assert result["recommended_treatment"].startswith("Developer compliance verification required before support")
