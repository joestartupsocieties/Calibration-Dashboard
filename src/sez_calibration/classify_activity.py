from __future__ import annotations

import pandas as pd

from .utils import safe_divide, to_float


ACTIVITY_COLUMNS = [
    "zone_id",
    "zone_name",
    "production_share_of_industrial_land",
    "production_share_of_allotted_land",
    "construction_share_of_allotted_land",
    "vacant_share_of_allotted_land",
    "colonization_share",
    "activity_category",
    "activity_reason",
]


def classify_activity(zone_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, zone in zone_df.iterrows():
        production = to_float(zone.get("under_production_area_acres")) or 0.0
        construction = to_float(zone.get("under_construction_area_acres")) or 0.0
        allotted = to_float(zone.get("allotted_area_acres")) or 0.0
        industrial = to_float(zone.get("industrial_area_acres")) or 0.0
        vacant = to_float(zone.get("vacant_area_acres")) or 0.0
        boundary_wall_only = to_float(zone.get("boundary_wall_only_area_acres")) or 0.0
        unsold = to_float(zone.get("unsold_area_acres")) or 0.0
        status_text = str(zone.get("operational_status") or "").strip().lower()

        prod_industrial = safe_divide(production, industrial)
        prod_allotted = safe_divide(production, allotted)
        construction_allotted = safe_divide(construction, allotted)
        vacant_allotted = safe_divide(vacant, allotted)
        boundary_allotted = safe_divide(boundary_wall_only, allotted)
        colonization = safe_divide(allotted, industrial)
        unsold_share = safe_divide(unsold, industrial)

        category, reason = _classify(
            production,
            construction,
            allotted,
            prod_allotted,
            construction_allotted,
            vacant_allotted,
            boundary_allotted,
            unsold_share,
            status_text,
        )
        rows.append(
            {
                "zone_id": zone.get("zone_id"),
                "zone_name": zone.get("zone_name"),
                "production_share_of_industrial_land": _round_or_na(prod_industrial),
                "production_share_of_allotted_land": _round_or_na(prod_allotted),
                "construction_share_of_allotted_land": _round_or_na(construction_allotted),
                "vacant_share_of_allotted_land": _round_or_na(vacant_allotted),
                "colonization_share": _round_or_na(colonization),
                "activity_category": category,
                "activity_reason": reason,
            }
        )
    return pd.DataFrame(rows, columns=ACTIVITY_COLUMNS)


def classify_activity_row(row: dict[str, object]) -> str:
    return str(classify_activity(pd.DataFrame([row])).loc[0, "activity_category"])


def _classify(
    production: float,
    construction: float,
    allotted: float,
    prod_allotted: float | None,
    construction_allotted: float | None,
    vacant_allotted: float | None,
    boundary_allotted: float | None,
    unsold_share: float | None,
    status_text: str = "",
) -> tuple[str, str]:
    if "under construction" in status_text and "under production" not in status_text and "production" not in status_text:
        return "moving_toward_production", "Reported status is under construction, so the zone is treated as construction-stage rather than operating."
    if "under production" in status_text or "commercial production" in status_text:
        return "operating_productive", "Reported status indicates production or commercial production."
    if production > 0 or (prod_allotted is not None and prod_allotted >= 0.10):
        return "operating_productive", "Reported production area or production share meets the screening threshold."
    if construction > 0 or (construction_allotted is not None and construction_allotted >= 0.10):
        return "moving_toward_production", "Construction area or construction share meets the transition threshold."
    if (
        "vacant" in status_text
        or "boundary" in status_text
        or (vacant_allotted is not None and vacant_allotted >= 0.50)
        or (boundary_allotted is not None and boundary_allotted > 0)
        or (unsold_share is not None and unsold_share >= 0.50)
    ):
        return "vacant_or_speculative", "Vacant, boundary-wall-only, or unsold land evidence is high."
    if allotted > 0 and production == 0 and construction == 0:
        return "allotted_but_inactive", "Land is allotted but no production or construction area is reported."
    return "unclear", "Available data do not support a clear activity category."


def _round_or_na(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)
