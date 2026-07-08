from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import ensure_dir


LEGAL_FIELDS = [
    "zone_id",
    "zone_name",
    "legal_risk_level",
    "developer_compliance_status",
    "enterprise_compliance_status",
    "legal_review_required",
]

FISCAL_FIELDS = [
    "zone_id",
    "zone_name",
    "fiscal_exposure_level",
    "fiscal_data_status",
]

LEGAL_FISCAL_PLACEHOLDER_FILE = "legal_fiscal_placeholders.csv"
PLACEHOLDER_FIELDS = [
    "zone_id",
    "zone_name",
    "legal_risk_level",
    "developer_compliance_status",
    "enterprise_compliance_status",
    "legal_review_required",
    "fiscal_exposure_level",
    "fiscal_data_status",
    "notes",
]

LEGAL_DEFAULTS = {
    "legal_risk_level": "unknown",
    "developer_compliance_status": "unknown",
    "enterprise_compliance_status": "unknown",
    "legal_review_required": True,
}

FISCAL_DEFAULTS = {
    "fiscal_exposure_level": "unknown",
    "fiscal_data_status": "missing",
    "notes": "Legal/fiscal placeholders pending D4 legal review and D5 fiscal verification.",
}


def ensure_placeholder_tables(zone_df: pd.DataFrame, data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    legal, fiscal, _metadata = ensure_placeholder_tables_with_metadata(zone_df, data_dir)
    return legal, fiscal


def ensure_placeholder_tables_with_metadata(zone_df: pd.DataFrame, data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    ensure_dir(data_dir)
    path = data_dir / LEGAL_FISCAL_PLACEHOLDER_FILE
    placeholders_created = not path.exists()
    combined = _ensure_table(
        path,
        zone_df,
        PLACEHOLDER_FIELDS,
        {**LEGAL_DEFAULTS, **FISCAL_DEFAULTS},
    )
    legal = combined[LEGAL_FIELDS].copy()
    fiscal = combined[FISCAL_FIELDS].copy()
    metadata = {
        "placeholder_file": str(path),
        "placeholders_created": bool(placeholders_created),
    }
    return legal, fiscal, metadata


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
