from __future__ import annotations

import pandas as pd

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
                "fiscal_data_confidence": fiscal_confidence,
            }
        ]
    )
    return zones, confidence, activity_df, legal, fiscal


def rec(**kwargs):
    return run_recommendation_engine(*base_frames(**kwargs)).iloc[0]


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
    assert result["recommended_treatment"] == "Sanction/cure review before support"
    assert "R15" in result["reason_codes"]


def test_productive_missing_fiscal_does_not_produce_final_eligibility() -> None:
    result = rec(activity="operating_productive", fiscal_exposure="unknown", fiscal_confidence="missing")
    assert "final" not in result["recommended_treatment"].lower()
    assert "pending D4 legal and D5 fiscal review" in result["recommended_treatment"]


def test_every_recommendation_has_reason_codes() -> None:
    result = rec()
    assert len([part for part in result["reason_codes"].split(";") if part.strip()]) >= 2
