from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sez_calibration.classify_activity import classify_activity_row


def test_production_area_gives_operating_productive() -> None:
    assert classify_activity_row({"zone_id": "Z1", "zone_name": "A", "under_production_area_acres": 1, "allotted_area_acres": 10, "industrial_area_acres": 20}) == "operating_productive"


def test_construction_area_gives_moving_toward_production() -> None:
    assert classify_activity_row({"zone_id": "Z1", "zone_name": "A", "under_construction_area_acres": 1, "allotted_area_acres": 10, "industrial_area_acres": 20}) == "moving_toward_production"


def test_allotted_area_without_activity_gives_inactive() -> None:
    assert classify_activity_row({"zone_id": "Z1", "zone_name": "A", "allotted_area_acres": 10, "industrial_area_acres": 20, "under_production_area_acres": 0, "under_construction_area_acres": 0, "vacant_area_acres": 1}) == "allotted_but_inactive"


def test_high_vacant_share_gives_speculative() -> None:
    assert classify_activity_row({"zone_id": "Z1", "zone_name": "A", "allotted_area_acres": 10, "industrial_area_acres": 20, "under_production_area_acres": 0, "under_construction_area_acres": 0, "vacant_area_acres": 8}) == "vacant_or_speculative"
