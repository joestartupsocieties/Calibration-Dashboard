from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import ensure_dir


LEGAL_FIELDS = [
    "zone_id",
    "zone_name",
    "development_agreement_status",
    "legal_risk_level",
    "grandfathering_risk",
    "developer_compliance_status",
    "enterprise_compliance_status",
    "reform_space",
    "legal_review_required",
    "legal_notes",
]

FISCAL_FIELDS = [
    "zone_id",
    "zone_name",
    "cit_foregone",
    "customs_duties_foregone",
    "land_concession_value",
    "infrastructure_public_cost",
    "utility_subsidy_or_psdp_cost",
    "administrative_cost",
    "tax_paid",
    "net_direct_fiscal_position",
    "fiscal_exposure_level",
    "fiscal_data_confidence",
    "fiscal_notes",
]

LEGAL_DEFAULTS = {
    "development_agreement_status": "unknown",
    "legal_risk_level": "unknown",
    "grandfathering_risk": "unknown",
    "developer_compliance_status": "unknown",
    "enterprise_compliance_status": "unknown",
    "reform_space": "unknown",
    "legal_review_required": True,
    "legal_notes": "Placeholder pending D4 legal review.",
}

FISCAL_DEFAULTS = {
    "cit_foregone": pd.NA,
    "customs_duties_foregone": pd.NA,
    "land_concession_value": pd.NA,
    "infrastructure_public_cost": pd.NA,
    "utility_subsidy_or_psdp_cost": pd.NA,
    "administrative_cost": pd.NA,
    "tax_paid": pd.NA,
    "net_direct_fiscal_position": pd.NA,
    "fiscal_exposure_level": "unknown",
    "fiscal_data_confidence": "missing",
    "fiscal_notes": "Placeholder pending D5/FBR/customs fiscal verification.",
}


def ensure_placeholder_tables(zone_df: pd.DataFrame, data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ensure_dir(data_dir)
    legal = _ensure_table(data_dir / "legal_compliance_placeholder.csv", zone_df, LEGAL_FIELDS, LEGAL_DEFAULTS)
    fiscal = _ensure_table(data_dir / "fiscal_exposure_placeholder.csv", zone_df, FISCAL_FIELDS, FISCAL_DEFAULTS)
    return legal, fiscal


def _ensure_table(path: Path, zone_df: pd.DataFrame, fields: list[str], defaults: dict[str, object]) -> pd.DataFrame:
    if path.exists():
        existing = pd.read_csv(path, encoding="utf-8-sig")
    else:
        existing = pd.DataFrame(columns=fields)

    rows = []
    existing_by_id = {str(row.get("zone_id")): row for _, row in existing.iterrows()} if "zone_id" in existing.columns else {}
    for _, zone in zone_df.iterrows():
        zone_id = str(zone.get("zone_id"))
        base = {"zone_id": zone_id, "zone_name": zone.get("zone_name")}
        base.update(defaults)
        if zone_id in existing_by_id:
            for field in fields:
                value = existing_by_id[zone_id].get(field)
                if pd.notna(value) and str(value).strip() != "":
                    base[field] = value
        rows.append(base)

    table = pd.DataFrame(rows, columns=fields)
    table.to_csv(path, index=False, encoding="utf-8")
    return table
