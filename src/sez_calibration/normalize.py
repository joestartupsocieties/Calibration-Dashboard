from __future__ import annotations

from collections import Counter
from typing import Any

import pandas as pd

from .utils import normalize_column_name


EXPECTED_ZONE_COLUMNS = [
    "zone_id",
    "zone_name",
    "province",
    "developer_name",
    "developer_mode",
    "zone_type",
    "operational_status",
    "total_area_acres",
    "industrial_area_acres",
    "allotted_area_acres",
    "vacant_area_acres",
    "under_construction_area_acres",
    "under_production_area_acres",
    "boundary_wall_only_area_acres",
    "unsold_area_acres",
    "number_allottees",
    "electricity_status",
    "gas_status",
    "water_status",
    "wastewater_status",
    "roads_status",
    "source_file",
    "source_row",
]

NUMERIC_FIELDS = [
    "total_area_acres",
    "industrial_area_acres",
    "allotted_area_acres",
    "vacant_area_acres",
    "under_construction_area_acres",
    "under_production_area_acres",
    "boundary_wall_only_area_acres",
    "unsold_area_acres",
    "number_allottees",
]

SYNONYMS = {
    "developer": "developer_name",
    "developer_type": "developer_mode",
    "notified_area_acres": "total_area_acres",
    "total_area": "total_area_acres",
    "area_acres": "total_area_acres",
    "unallotted_area_acres": "unsold_area_acres",
    "area_unsold_acres": "unsold_area_acres",
    "number_of_allottees": "number_allottees",
    "allottees": "number_allottees",
    "road_status": "roads_status",
    "roads": "roads_status",
    "source_sheet": "source_file",
    "source_rows": "source_row",
    "source": "source_file",
    "confidence_level": "data_confidence",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = _dedupe_columns([normalize_column_name(col) for col in df.columns])

    for source, target in SYNONYMS.items():
        if source in df.columns:
            if target not in df.columns:
                df[target] = df[source]
            else:
                df[target] = df[target].where(df[target].notna() & (df[target].astype(str).str.strip() != ""), df[source])

    if "zone_id" not in df.columns:
        df.insert(0, "zone_id", [f"SEZ-{i:03d}" for i in range(1, len(df) + 1)])

    for field in EXPECTED_ZONE_COLUMNS:
        if field not in df.columns:
            df[field] = pd.NA

    for field in NUMERIC_FIELDS:
        df[field] = pd.to_numeric(df[field], errors="coerce")

    df["zone_name"] = df["zone_name"].fillna("").astype(str).str.strip()
    df["province"] = df["province"].fillna("").astype(str).str.strip()
    df["source_file"] = df["source_file"].fillna("").astype(str).str.strip()
    df["source_row"] = df["source_row"].fillna("").astype(str).str.strip()
    if "data_confidence" in df.columns:
        df["data_confidence"] = df["data_confidence"].fillna("").astype(str).str.strip()

    ordered = EXPECTED_ZONE_COLUMNS + [col for col in df.columns if col not in EXPECTED_ZONE_COLUMNS]
    return df[ordered]


def _dedupe_columns(columns: list[str]) -> list[str]:
    counts: Counter[str] = Counter()
    out: list[str] = []
    for col in columns:
        counts[col] += 1
        if counts[col] == 1:
            out.append(col)
        else:
            out.append(f"{col}_{counts[col]}")
    return out


def sample_zone_rows() -> list[dict[str, Any]]:
    return [
        {
            "zone_id": f"DEMO-{i:03d}",
            "zone_name": name,
            "province": province,
            "developer_name": "Demo Developer",
            "developer_mode": "demo",
            "zone_type": "Demo multi-industry SEZ",
            "operational_status": status,
            "total_area_acres": total,
            "industrial_area_acres": industrial,
            "allotted_area_acres": allotted,
            "vacant_area_acres": vacant,
            "under_construction_area_acres": construction,
            "under_production_area_acres": production,
            "unsold_area_acres": unsold,
            "number_allottees": allottees,
            "number_of_zone_enterprises": enterprises,
            "electricity_status": "Demo data",
            "gas_status": "Demo data",
            "water_status": "Demo data",
            "wastewater_status": "Demo data",
            "roads_status": "Demo data",
            "source_file": "generated_demo_sample",
            "source_row": str(i),
            "data_confidence": "demo sample",
            "demo_data_flag": True,
        }
        for i, (name, province, status, total, industrial, allotted, vacant, construction, production, unsold, allottees, enterprises) in enumerate(
            [
                ("Demo Productive Zone", "Punjab", "Under Production", 500, 350, 200, 20, 30, 80, 150, 12, 10),
                ("Demo Construction Zone", "Sindh", "Under Construction", 300, 220, 120, 20, 50, 0, 100, 5, 3),
                ("Demo Inactive Zone", "Balochistan", "Allotted", 180, 120, 80, 5, 0, 0, 40, 4, 1),
                ("Demo Vacant Zone", "Khyber Pakhtunkhwa", "Vacant", 250, 160, 100, 70, 0, 0, 60, 2, 0),
                ("Demo Data Gap Zone", "", "", 150, None, None, None, None, None, None, None, None),
                ("Demo Utility Constraint Zone", "Punjab", "Under Construction", 200, 160, 90, 10, 25, 0, 70, 6, 2),
                ("Demo Sole Enterprise Zone", "Sindh", "Under Production", 75, 60, 55, 0, 0, 55, 5, 1, 1),
                ("Demo Legal Review Zone", "Islamabad", "Operational", 90, 50, 30, 0, 0, 8, 20, 1, 1),
            ],
            start=1,
        )
    ]
