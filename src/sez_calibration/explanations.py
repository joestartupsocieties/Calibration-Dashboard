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
        next_actions = " | ".join(
            [
                clean_text(rec.get("required_data_action")),
                clean_text(rec.get("required_legal_action")),
                clean_text(rec.get("required_fbr_action")),
            ]
        )
        explanation = (
            f"{rec.get('zone_name')} receives the provisional treatment: {rec.get('recommended_treatment')}. "
            f"The screening result reflects activity category `{rec.get('activity_category')}`, data confidence "
            f"`{rec.get('data_confidence_band')}`, legal risk `{rec.get('legal_risk_level')}`, and fiscal exposure "
            f"`{rec.get('fiscal_exposure_level')}`. This is not final eligibility; human review, D4 legal review, "
            "and D5/FBR fiscal verification remain part of the required trail."
        )
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
    return " ".join(items)
