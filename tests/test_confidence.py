from __future__ import annotations

import pandas as pd

from sez_calibration.confidence import calculate_confidence_scores


def test_confidence_score_is_between_zero_and_one() -> None:
    rows = pd.DataFrame(
        [
            {
                "zone_id": "Z1",
                "zone_name": "Zone One",
                "province": "Punjab",
                "total_area_acres": 100,
                "industrial_area_acres": 80,
                "allotted_area_acres": 40,
                "under_production_area_acres": 10,
                "under_construction_area_acres": 5,
                "vacant_area_acres": 1,
                "operational_status": "Under Production",
                "source_file": "BOI survey 2026",
                "source_row": "1",
                "data_confidence": "high",
            }
        ]
    )
    score = calculate_confidence_scores(rows).loc[0, "data_confidence_score"]
    assert 0 <= score <= 1


def test_missing_critical_fields_reduce_confidence() -> None:
    complete = pd.DataFrame(
        [
            {
                "zone_id": "Z1",
                "zone_name": "Complete",
                "province": "Punjab",
                "total_area_acres": 100,
                "industrial_area_acres": 80,
                "allotted_area_acres": 40,
                "under_production_area_acres": 10,
                "under_construction_area_acres": 5,
                "vacant_area_acres": 1,
                "operational_status": "Under Production",
                "source_file": "BOI survey 2026",
                "source_row": "1",
                "data_confidence": "high",
            },
            {
                "zone_id": "Z2",
                "zone_name": "Sparse",
                "province": "",
                "total_area_acres": 100,
                "industrial_area_acres": None,
                "allotted_area_acres": None,
                "under_production_area_acres": None,
                "under_construction_area_acres": None,
                "vacant_area_acres": None,
                "operational_status": "",
                "source_file": "",
                "source_row": "",
                "data_confidence": "low",
            },
        ]
    )
    scores = calculate_confidence_scores(complete)
    assert scores.loc[0, "data_confidence_score"] > scores.loc[1, "data_confidence_score"]


def test_high_severity_issue_reduces_confidence() -> None:
    zone = pd.DataFrame(
        [
            {
                "zone_id": "Z1",
                "zone_name": "Zone One",
                "province": "Punjab",
                "total_area_acres": 100,
                "industrial_area_acres": 80,
                "allotted_area_acres": 40,
                "under_production_area_acres": 10,
                "under_construction_area_acres": 5,
                "vacant_area_acres": 1,
                "operational_status": "Under Production",
                "source_file": "BOI survey 2026",
                "source_row": "1",
                "data_confidence": "high",
            }
        ]
    )
    baseline = calculate_confidence_scores(zone).loc[0, "data_confidence_score"]
    issues = pd.DataFrame([{"zone_id": "Z1", "severity": "high"}])
    penalized = calculate_confidence_scores(zone, issues).loc[0, "data_confidence_score"]
    assert penalized < baseline
