from __future__ import annotations

import re
from difflib import SequenceMatcher

import pandas as pd

from .utils import clean_text, dataframe_from_rows, today_iso, to_float


ISSUE_COLUMNS = [
    "issue_id",
    "dataset_name",
    "zone_id",
    "zone_name",
    "field_name",
    "issue_type",
    "severity",
    "issue_description",
    "recommended_fix",
    "model_impact",
    "source_file",
    "source_row",
    "resolved_flag",
    "date_logged",
]

FIELD_COMPLETENESS_COLUMNS = [
    "field_name",
    "present_count",
    "missing_count",
    "completeness_pct",
    "criticality",
    "recommended_action",
]

CRITICAL_FIELDS = [
    "zone_name",
    "province",
    "total_area_acres",
    "industrial_area_acres",
    "allotted_area_acres",
    "under_production_area_acres",
    "under_construction_area_acres",
    "vacant_area_acres",
    "operational_status",
]

ACREAGE_FIELDS = [
    "total_area_acres",
    "industrial_area_acres",
    "allotted_area_acres",
    "vacant_area_acres",
    "under_construction_area_acres",
    "under_production_area_acres",
    "unsold_area_acres",
]

HIGH_ALLOTTED_ABSOLUTE_ACRES = 25.0
HIGH_ALLOTTED_INDUSTRIAL_SHARE = 0.50


def run_data_quality_checks(zone_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    issues: list[dict[str, object]] = []
    contradictions: list[dict[str, object]] = []

    def add(
        target: list[dict[str, object]],
        zone: pd.Series | None,
        field: str,
        issue_type: str,
        severity: str,
        description: str,
        fix: str,
        impact: str,
    ) -> None:
        zone_id = "ALL" if zone is None else clean_text(zone.get("zone_id"))
        zone_name = "All zones" if zone is None else clean_text(zone.get("zone_name"))
        source_file = "" if zone is None else clean_text(zone.get("source_file"))
        source_row = "" if zone is None else clean_text(zone.get("source_row"))
        target.append(
            {
                "issue_id": f"DQ-{len(issues) + len(contradictions) + 1:04d}",
                "dataset_name": "SEZ_Key_Indicators_Normalized.csv",
                "zone_id": zone_id,
                "zone_name": zone_name,
                "field_name": field,
                "issue_type": issue_type,
                "severity": severity,
                "issue_description": description,
                "recommended_fix": fix,
                "model_impact": impact,
                "source_file": source_file,
                "source_row": source_row,
                "resolved_flag": False,
                "date_logged": today_iso(),
            }
        )

    add(
        contradictions,
        None,
        "zone_universe",
        "source_scope",
        "critical",
        "Source digest and prior scaffold refer to different SEZ universes: 35 detected zone profile records / normalized indicator records, 44 notified zones, and 54 total including planning-stage zones.",
        "Keep explicit source-universe flags and do not generalize 35-zone outputs to the full registry without reconciliation.",
        "Comparability and denominator-sensitive policy conclusions may be wrong if universes are mixed.",
    )
    add(
        contradictions,
        None,
        "legal_and_fiscal_inputs",
        "warning",
        "high",
        "Legal and fiscal fields are placeholders pending D4 legal review and D5/FBR/customs fiscal verification.",
        "Replace placeholder tables with reviewed D4/D5 outputs before final decisions.",
        "The rule engine can screen zones but cannot make final incentive decisions.",
    )

    for _, zone in zone_df.iterrows():
        for field in CRITICAL_FIELDS:
            if _is_missing(zone.get(field)):
                add(
                    issues,
                    zone,
                    field,
                    "missing",
                    "critical" if field in {"zone_name", "operational_status"} else "high",
                    f"Critical field `{field}` is missing.",
                    "Verify against the original workbook/source digest and update the normalized CSV.",
                    "Recommendation confidence and hard-gate routing are weakened.",
                )

        for field in ACREAGE_FIELDS:
            value = to_float(zone.get(field))
            if value is not None and value < 0:
                add(
                    issues,
                    zone,
                    field,
                    "impossible_value",
                    "critical",
                    f"`{field}` is negative ({value}).",
                    "Correct the acreage value or mark it unknown with source notes.",
                    "Land-use ratios and treatment recommendations are unreliable.",
                )

        total = to_float(zone.get("total_area_acres"))
        industrial = to_float(zone.get("industrial_area_acres"))
        allotted = to_float(zone.get("allotted_area_acres"))
        production = to_float(zone.get("under_production_area_acres"))
        construction = to_float(zone.get("under_construction_area_acres"))
        vacant = to_float(zone.get("vacant_area_acres"))
        unsold = to_float(zone.get("unsold_area_acres"))

        if total is not None and industrial is not None and industrial > total:
            add(issues, zone, "industrial_area_acres", "impossible_value", "high", "Industrial area exceeds total area.", "Confirm total and industrial area in the original workbook.", "Utilization denominators are inconsistent.")
        if industrial is not None and allotted is not None and allotted > industrial * 1.25:
            add(issues, zone, "allotted_area_acres", "impossible_value", "high", "Allotted area is more than 125% of industrial area.", "Reconcile allotted and industrial area fields.", "Colonization share may be overstated.")
        if allotted is not None:
            for field, value in {
                "under_production_area_acres": production,
                "under_construction_area_acres": construction,
                "vacant_area_acres": vacant,
            }.items():
                if value is not None and value > allotted:
                    add(issues, zone, field, "impossible_value", "high", f"`{field}` exceeds allotted area.", "Verify plot-status acreage against source rows.", "Activity category may be wrong.")
            known_status_area = sum(v for v in [production, construction, vacant] if v is not None)
            if known_status_area > allotted * 1.25:
                add(issues, zone, "activity_area_total", "contradiction", "high", "Production + construction + vacant area exceeds 125% of allotted area.", "Add missing residual categories or reconcile status areas.", "The model cannot reliably classify productive use.")

        if industrial is not None and allotted is not None and unsold is not None:
            diff = (allotted + unsold) - industrial
            if abs(diff) > max(0.5, industrial * 0.05):
                add(contradictions, zone, "industrial/allotted/unsold_area", "contradiction", "medium", f"Allotted + unsold area differs from industrial area by {diff:.2f} acres.", "Retain both values with source notes and ask the source owner for the canonical denominator.", "Land-use percentages and fiscal cost-per-acre metrics may not reconcile.")

        status = clean_text(zone.get("operational_status")).lower()
        if status in {"unknown", "n/a", "na"}:
            add(issues, zone, "operational_status", "warning", "medium", "Operational status is unknown.", "Map raw status labels into a controlled status dictionary.", "Activity classification may default to unclear.")
        if _status_says_operational(status) and (production is None or production == 0):
            add(contradictions, zone, "operational_status/under_production_area_acres", "contradiction", "medium", "Status implies operation or production, but production area is zero or missing.", "Check enterprise rows and 2026 colonization metrics.", "Pilot screening may overstate productive activity.")
        if _status_says_non_operational(status) and production not in (None, 0):
            add(contradictions, zone, "operational_status/under_production_area_acres", "contradiction", "medium", "Status implies non-production, but production area is positive.", "Reconcile raw status and acreage source dates.", "Hard gates may route the zone inconsistently.")

        if _has_high_allotted_no_activity(allotted, industrial, production, construction):
            add(
                issues,
                zone,
                "allotted_area_acres",
                "stalled_activity",
                "high",
                "High allotted area is reported, but production and construction acreage are zero or missing.",
                "Verify enterprise activity, plot status, and construction data against source rows.",
                "Activity classification may route the zone as inactive despite high apparent land uptake.",
            )

        confidence_text = clean_text(zone.get("data_confidence")).lower()
        if "no 2026 colonization match" in confidence_text:
            add(issues, zone, "2026_colonization_metrics", "warning", "high", "No 2026 colonization match is indicated in source confidence notes.", "Reconcile zone aliases against the colonization comparison workbook.", "Movement and activity scores are provisional.")
        if "differs from colonization total" in confidence_text:
            add(contradictions, zone, "total_area_acres", "contradiction", "high", clean_text(zone.get("data_confidence")), "Keep both area values with dates and confirm canonical area.", "Area-based comparisons may not be stable.")

    _add_duplicate_name_checks(zone_df, issues, add)

    issue_df = dataframe_from_rows(issues, ISSUE_COLUMNS)
    contradiction_df = dataframe_from_rows(contradictions, ISSUE_COLUMNS)
    completeness_df = field_completeness(zone_df)
    return issue_df, contradiction_df, completeness_df


def field_completeness(zone_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for field in zone_df.columns:
        missing = int(zone_df[field].isna().sum() + (zone_df[field].fillna("").astype(str).str.strip() == "").sum() - zone_df[field].isna().sum())
        present = int(len(zone_df) - missing)
        pct = present / len(zone_df) if len(zone_df) else 0
        criticality = "critical" if field in CRITICAL_FIELDS else "standard"
        action = "No immediate action" if pct == 1 else "Verify, normalize, or leave explicitly flagged as missing."
        rows.append(
            {
                "field_name": field,
                "present_count": present,
                "missing_count": missing,
                "completeness_pct": round(pct, 4),
                "criticality": criticality,
                "recommended_action": action,
            }
        )
    return pd.DataFrame(rows, columns=FIELD_COMPLETENESS_COLUMNS)


def _is_missing(value: object) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip() == ""


def _status_says_operational(status: str) -> bool:
    if _status_says_non_operational(status):
        return False
    return any(token in status for token in ["operational", "under production", "in production", "production", "operating"])


def _status_says_non_operational(status: str) -> bool:
    return any(
        token in status
        for token in [
            "non-operational",
            "non operational",
            "not operational",
            "vacant",
            "only boundary wall",
            "boundary wall only",
        ]
    )


def _has_high_allotted_no_activity(
    allotted: float | None,
    industrial: float | None,
    production: float | None,
    construction: float | None,
) -> bool:
    if allotted is None or allotted <= 0:
        return False
    if production not in (None, 0) or construction not in (None, 0):
        return False
    share_threshold = industrial * HIGH_ALLOTTED_INDUSTRIAL_SHARE if industrial is not None and industrial > 0 else 0
    return allotted >= max(HIGH_ALLOTTED_ABSOLUTE_ACRES, share_threshold)


def _canonical_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower().replace("specialeconomiczone", "sez"))


def _add_duplicate_name_checks(zone_df: pd.DataFrame, issues: list[dict[str, object]], add) -> None:
    seen: dict[str, pd.Series] = {}
    rows = [row for _, row in zone_df.iterrows()]
    for row in rows:
        key = _canonical_name(clean_text(row.get("zone_name")))
        if not key:
            continue
        if key in seen:
            add(issues, row, "zone_name", "contradiction", "high", "Duplicate or canonical-equivalent zone name detected.", "Create a canonical zone alias table and confirm whether records should merge.", "Legal, fiscal, and activity joins may duplicate a zone.")
        seen[key] = row

    for idx, left in enumerate(rows):
        left_name = clean_text(left.get("zone_name"))
        if not left_name:
            continue
        for right in rows[idx + 1 :]:
            right_name = clean_text(right.get("zone_name"))
            if not right_name or left_name == right_name:
                continue
            score = SequenceMatcher(None, _canonical_name(left_name), _canonical_name(right_name)).ratio()
            if score >= 0.95:
                add(issues, right, "zone_name", "warning", "low", f"Zone name is highly similar to `{left_name}`.", "Review alias/canonical name mapping.", "Joins across legal, fiscal, and source tables may be brittle.")
