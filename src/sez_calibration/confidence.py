from __future__ import annotations

import pandas as pd

from .data_quality import CRITICAL_FIELDS
from .utils import clean_text, to_float


CONFIDENCE_COLUMNS = [
    "zone_id",
    "zone_name",
    "completeness_score",
    "internal_consistency_score",
    "source_availability_score",
    "recency_source_note_score",
    "data_confidence_score",
    "data_confidence_band",
    "confidence_reason",
]

WEIGHTS = {
    "completeness": 0.40,
    "internal_consistency": 0.30,
    "source_availability": 0.20,
    "recency_source_note": 0.10,
}


def calculate_confidence_scores(zone_df: pd.DataFrame, issue_df: pd.DataFrame | None = None) -> pd.DataFrame:
    issue_df = issue_df if issue_df is not None else pd.DataFrame()
    rows: list[dict[str, object]] = []
    for _, zone in zone_df.iterrows():
        completeness, completeness_reason = _completeness(zone)
        consistency, consistency_reason = _internal_consistency(zone, issue_df)
        source_availability, source_reason = _source_availability(zone)
        recency, recency_reason = _recency_source_note(zone)
        score = (
            completeness * WEIGHTS["completeness"]
            + consistency * WEIGHTS["internal_consistency"]
            + source_availability * WEIGHTS["source_availability"]
            + recency * WEIGHTS["recency_source_note"]
        )
        score = max(0.0, min(1.0, score))
        rows.append(
            {
                "zone_id": zone.get("zone_id"),
                "zone_name": zone.get("zone_name"),
                "completeness_score": round(completeness, 4),
                "internal_consistency_score": round(consistency, 4),
                "source_availability_score": round(source_availability, 4),
                "recency_source_note_score": round(recency, 4),
                "data_confidence_score": round(score, 4),
                "data_confidence_band": confidence_band(score),
                "confidence_reason": " | ".join([completeness_reason, consistency_reason, source_reason, recency_reason]),
            }
        )
    return pd.DataFrame(rows, columns=CONFIDENCE_COLUMNS)


def confidence_band(score: float) -> str:
    if score >= 0.80:
        return "high"
    if score >= 0.60:
        return "medium"
    if score >= 0.40:
        return "low"
    return "do_not_use"


def _completeness(zone: pd.Series) -> tuple[float, str]:
    present = 0
    for field in CRITICAL_FIELDS:
        value = zone.get(field)
        if value is not None and not pd.isna(value) and str(value).strip() != "":
            present += 1
    score = present / len(CRITICAL_FIELDS)
    return score, f"{present}/{len(CRITICAL_FIELDS)} critical fields present"


def _internal_consistency(zone: pd.Series, issue_df: pd.DataFrame) -> tuple[float, str]:
    if issue_df.empty:
        return 1.0, "no zone-level quality issues logged"
    zone_issues = issue_df[issue_df["zone_id"].astype(str) == str(zone.get("zone_id"))]
    penalty = 0.0
    weights = {"critical": 0.28, "high": 0.16, "medium": 0.08, "low": 0.03}
    for severity in zone_issues.get("severity", []):
        penalty += weights.get(str(severity).lower(), 0.05)
    score = max(0.0, 1.0 - penalty)
    return score, f"{len(zone_issues)} data-quality issue(s) reduce internal consistency"


def _source_availability(zone: pd.Series) -> tuple[float, str]:
    has_source_file = bool(clean_text(zone.get("source_file")))
    has_source_row = bool(clean_text(zone.get("source_row")))
    has_source_note = bool(clean_text(zone.get("data_confidence")))
    if has_source_file and has_source_row:
        return 1.0, "source file and source row are available"
    if has_source_file:
        return 0.75, "source file is available, but source row is missing"
    if has_source_row:
        return 0.50, "source row is available, but source file is missing"
    if has_source_note:
        return 0.25, "source note is available, but source file and row are missing"
    return 0.0, "source file, row, and note are missing"


def _recency_source_note(zone: pd.Series) -> tuple[float, str]:
    text = f"{zone.get('source_file', '')} {zone.get('source_row', '')} {zone.get('data_confidence', '')} {zone.get('operational_status', '')}".lower()
    if "no 2026 colonization match" in text:
        return 0.45, "no 2026 colonization match indicated"
    if "2026" in text:
        return 1.0, "2026 evidence indicated"
    if "colonization" in text:
        return 0.80, "colonization evidence indicated"
    if "2025" in text or "2024" in text:
        return 0.65, "recent source note indicated"
    if clean_text(zone.get("data_confidence")):
        return 0.50, "source note retained, but recency is not explicit"
    return 0.35, "recency and source note are not explicit"


def score_single_zone(zone: dict[str, object], issues: pd.DataFrame | None = None) -> float:
    df = pd.DataFrame([zone])
    result = calculate_confidence_scores(df, issues)
    return float(to_float(result.loc[0, "data_confidence_score"]) or 0.0)
