from __future__ import annotations

import pandas as pd

from .data_quality import CRITICAL_FIELDS
from .utils import clean_text, to_float


CONFIDENCE_COLUMNS = [
    "zone_id",
    "zone_name",
    "source_reliability_score",
    "completeness_score",
    "internal_consistency_score",
    "cross_source_consistency_score",
    "recency_score",
    "data_confidence_score",
    "data_confidence_band",
    "confidence_reason",
]

WEIGHTS = {
    "source_reliability": 0.25,
    "completeness": 0.25,
    "internal_consistency": 0.20,
    "cross_source_consistency": 0.20,
    "recency": 0.10,
}


def calculate_confidence_scores(zone_df: pd.DataFrame, issue_df: pd.DataFrame | None = None) -> pd.DataFrame:
    issue_df = issue_df if issue_df is not None else pd.DataFrame()
    rows: list[dict[str, object]] = []
    for _, zone in zone_df.iterrows():
        source_reliability, source_reason = _source_reliability(zone)
        completeness, completeness_reason = _completeness(zone)
        consistency, consistency_reason = _internal_consistency(zone, issue_df)
        cross_source, cross_reason = _cross_source_consistency(zone)
        recency, recency_reason = _recency(zone)
        score = (
            source_reliability * WEIGHTS["source_reliability"]
            + completeness * WEIGHTS["completeness"]
            + consistency * WEIGHTS["internal_consistency"]
            + cross_source * WEIGHTS["cross_source_consistency"]
            + recency * WEIGHTS["recency"]
        )
        score = max(0.0, min(1.0, score))
        rows.append(
            {
                "zone_id": zone.get("zone_id"),
                "zone_name": zone.get("zone_name"),
                "source_reliability_score": round(source_reliability, 4),
                "completeness_score": round(completeness, 4),
                "internal_consistency_score": round(consistency, 4),
                "cross_source_consistency_score": round(cross_source, 4),
                "recency_score": round(recency, 4),
                "data_confidence_score": round(score, 4),
                "data_confidence_band": confidence_band(score),
                "confidence_reason": " | ".join([source_reason, completeness_reason, consistency_reason, cross_reason, recency_reason]),
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


def _source_reliability(zone: pd.Series) -> tuple[float, str]:
    text = f"{zone.get('data_confidence', '')} {zone.get('source_file', '')}".lower()
    score = 0.55
    if "high" in text:
        score = 0.90
    elif "medium" in text:
        score = 0.70
    elif "low" in text:
        score = 0.45
    if any(token in text for token in ["boi", "survey", "colonization", "data "]):
        score = min(1.0, score + 0.05)
    if clean_text(zone.get("source_row")):
        score = min(1.0, score + 0.03)
    return score, f"source reliability {score:.2f} based on source/confidence notes"


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


def _cross_source_consistency(zone: pd.Series) -> tuple[float, str]:
    note = clean_text(zone.get("data_confidence")).lower()
    if "differs from colonization total" in note or "conflict" in note:
        return 0.50, "cross-source consistency not fully calculable; conflict note retained"
    return 0.50, "cross-source consistency not fully calculable in MVP; defaulted to 0.50"


def _recency(zone: pd.Series) -> tuple[float, str]:
    text = f"{zone.get('source_file', '')} {zone.get('source_row', '')} {zone.get('data_confidence', '')} {zone.get('operational_status', '')}".lower()
    if "no 2026 colonization match" in text:
        return 0.45, "no 2026 colonization match indicated"
    if "2026" in text or "colonization" in text:
        return 0.80, "2026/colonization evidence indicated"
    if "2024" in text:
        return 0.65, "2024 evidence indicated"
    return 0.55, "recency not explicit; medium placeholder applied"


def score_single_zone(zone: dict[str, object], issues: pd.DataFrame | None = None) -> float:
    df = pd.DataFrame([zone])
    result = calculate_confidence_scores(df, issues)
    return float(to_float(result.loc[0, "data_confidence_score"]) or 0.0)
