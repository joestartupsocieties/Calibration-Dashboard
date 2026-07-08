from __future__ import annotations

import pandas as pd

from .utils import clean_text


EXPLANATION_COLUMNS = [
    "zone_id",
    "zone_name",
    "recommendation_summary",
    "plain_english_explanation",
    "reason_codes",
    "data_limitations",
    "next_actions",
]


def build_recommendation_explanations(recommendations: pd.DataFrame, reason_codes: dict[str, str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, rec in recommendations.iterrows():
        code_list = split_reason_codes(rec.get("reason_codes"))
        decoded = "; ".join(f"{code}: {reason_codes.get(code, 'Unmapped reason code')}" for code in code_list)
        limitations = _limitations(rec)
        next_actions = clean_text(rec.get("next_actions")) or " | ".join(
            [
                clean_text(rec.get("required_data_action")),
                clean_text(rec.get("required_legal_action")),
                clean_text(rec.get("required_fbr_action")),
            ]
        )
        explanation = clean_text(rec.get("why")) or _memo(rec)
        rows.append(
            {
                "zone_id": rec.get("zone_id"),
                "zone_name": rec.get("zone_name"),
                "recommendation_summary": rec.get("recommended_treatment"),
                "plain_english_explanation": explanation,
                "reason_codes": decoded,
                "data_limitations": limitations,
                "next_actions": next_actions,
            }
        )
    return pd.DataFrame(rows, columns=EXPLANATION_COLUMNS)


def split_reason_codes(codes: object) -> list[str]:
    return [part.strip() for part in clean_text(codes).replace(",", ";").split(";") if part.strip()]


def _limitations(rec: pd.Series) -> str:
    items = [
        "Recommendations are provisional and for demonstration only.",
        "Exact row-level verification should use the original workbook.",
    ]
    if rec.get("fiscal_exposure_level") == "unknown":
        items.append("Fiscal exposure is a placeholder pending D5/FBR/customs verification.")
    if rec.get("legal_risk_level") == "unknown":
        items.append("Legal risk is a placeholder pending D4 legal review.")
    if rec.get("data_confidence_band") in {"low", "do_not_use"}:
        items.append("Data confidence is too weak for reliable screening.")
    if rec.get("additionality_confidence") in {"Unknown", "Low"}:
        items.append("Additionality and net fiscal/economic impact require separate validation.")
    return " ".join(items)


def _memo(rec: pd.Series) -> str:
    zone_name = clean_text(rec.get("zone_name")) or "This zone"
    activity = clean_text(rec.get("activity_category"))
    confidence = clean_text(rec.get("data_confidence_band"))
    treatment = clean_text(rec.get("recommended_treatment")).rstrip(".")
    legal_unknown = clean_text(rec.get("legal_risk_level")).lower() in {"", "unknown"}
    fiscal_unknown = clean_text(rec.get("fiscal_exposure_level")).lower() in {"", "unknown"}

    if activity == "operating_productive" and confidence in {"medium", "high"}:
        because = "reported data shows production activity and medium/high data confidence"
    elif activity == "moving_toward_production":
        because = "reported data shows construction activity but not yet production"
    elif activity == "vacant_or_speculative":
        because = "reported data shows high vacant or unsold land share"
    elif activity == "allotted_but_inactive":
        because = "reported data shows allotment-only movement with weak evidence of productive use"
    elif confidence in {"low", "do_not_use"}:
        because = "data confidence is not strong enough for a pilot screen"
    else:
        because = "the current data does not support a clear activity classification"

    treatment_lower = treatment.lower()
    if "possible pilot screen candidate" in treatment_lower:
        opening = f"{zone_name} is a possible pilot screen candidate because {because}."
    elif "possible transition candidate" in treatment_lower:
        opening = f"{zone_name} is a possible transition candidate because {because}."
    elif "more data required" in treatment_lower:
        opening = f"{zone_name} requires more data before a screening decision because {because}."
    elif "human review required" in treatment_lower:
        opening = f"{zone_name} requires human review because {because}."
    elif "no new temporary transition support" in treatment_lower:
        opening = f"{zone_name} does not currently pass the transition review screen because {because}."
    elif "sanction/cure review" in treatment_lower:
        opening = f"{zone_name} requires sanction/cure review because {because}."
    elif "developer compliance verification" in treatment_lower:
        opening = f"{zone_name} requires developer compliance verification because {because}."
    else:
        opening = f"{zone_name} needs additional review because {because}."

    placeholder_reason = "legal classification and fiscal exposure are placeholders"
    if legal_unknown and not fiscal_unknown:
        placeholder_reason = "legal classification is a placeholder"
    elif fiscal_unknown and not legal_unknown:
        placeholder_reason = "fiscal exposure is a placeholder"

    return (
        f"{opening} However, final support cannot be recommended because {placeholder_reason}. "
        "D4 legal review, D5 fiscal verification, FBR/customs data, and human review are required."
    )
