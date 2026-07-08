from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .classify_activity import classify_activity
from .confidence import calculate_confidence_scores
from .data_quality import run_data_quality_checks
from .explanations import build_recommendation_explanations
from .ingest import load_zone_data_with_metadata
from .legal_compliance import ensure_placeholder_tables_with_metadata
from .recommendation_engine import load_reason_codes, run_recommendation_engine
from .utils import PROJECT_ROOT, ensure_dir, write_csv, write_json


REQUIRED_OUTPUTS = [
    "zone_triage_prototype.csv",
    "recommendation_explanations.csv",
    "audit_flags.csv",
    "data_quality_issue_log.csv",
    "contradiction_log.csv",
    "data_confidence_scores.csv",
    "activity_classification.csv",
    "summary.json",
    "sez_calibration_demo_outputs.xlsx",
]


def run_pipeline(
    project_root: Path | None = None,
    scenario: dict[str, Any] | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    root = Path(project_root) if project_root else PROJECT_ROOT
    data_dir = ensure_dir(root / "data")
    config_dir = ensure_dir(root / "config")
    output_dir = ensure_dir(root / "outputs")

    zones, ingest_metadata = load_zone_data_with_metadata(data_dir)
    legal, fiscal, placeholder_metadata = ensure_placeholder_tables_with_metadata(zones, data_dir)
    issues, contradictions, field_completeness = run_data_quality_checks(zones)
    consistency_inputs = pd.concat([issues, contradictions], ignore_index=True)
    confidence = calculate_confidence_scores(zones, consistency_inputs)
    activity = classify_activity(zones)
    recommendations = run_recommendation_engine(zones, confidence, activity, legal, fiscal, issues, scenario)
    reason_codes = load_reason_codes(config_dir / "reason_codes_v0_5_lite.yaml")
    explanations = build_recommendation_explanations(recommendations, reason_codes)
    audit_flags = build_audit_flags(issues, contradictions, recommendations)
    summary = build_summary(zones, issues, contradictions, confidence, activity, recommendations)
    summary.update(ingest_metadata)
    summary.update(placeholder_metadata)

    frames = {
        "zones": zones,
        "legal": legal,
        "fiscal": fiscal,
        "issues": issues,
        "contradictions": contradictions,
        "field_completeness": field_completeness,
        "confidence": confidence,
        "activity": activity,
        "recommendations": recommendations,
        "explanations": explanations,
        "audit_flags": audit_flags,
    }

    if write_outputs:
        write_csv(recommendations, output_dir / "zone_triage_prototype.csv")
        write_csv(explanations, output_dir / "recommendation_explanations.csv")
        write_csv(audit_flags, output_dir / "audit_flags.csv")
        write_csv(issues, output_dir / "data_quality_issue_log.csv")
        write_csv(contradictions, output_dir / "contradiction_log.csv")
        write_csv(confidence, output_dir / "data_confidence_scores.csv")
        write_csv(activity, output_dir / "activity_classification.csv")
        write_csv(field_completeness, output_dir / "field_completeness.csv")
        write_json(summary, output_dir / "summary.json")
        export_excel(output_dir / "sez_calibration_demo_outputs.xlsx", summary, frames, reason_codes)

    return {"summary": summary, "frames": frames, "output_dir": output_dir}


def build_audit_flags(issues: pd.DataFrame, contradictions: pd.DataFrame, recommendations: pd.DataFrame) -> pd.DataFrame:
    severe_issues = pd.concat([issues, contradictions], ignore_index=True)
    if not severe_issues.empty:
        severe_issues = severe_issues[severe_issues["severity"].astype(str).str.lower().isin(["critical", "high"])]
    rec_flags = recommendations[
        (recommendations["hard_gates_triggered"].astype(str) != "none")
        | (recommendations["possible_screen_candidate_flag"].astype(bool))
    ][["zone_id", "zone_name", "hard_gates_triggered", "reason_codes", "recommended_treatment"]].copy()
    rec_flags["issue_id"] = [f"REC-{i:04d}" for i in range(1, len(rec_flags) + 1)]
    rec_flags["dataset_name"] = "zone_triage_prototype.csv"
    rec_flags["field_name"] = "recommendation"
    rec_flags["issue_type"] = "recommendation_flag"
    rec_flags["severity"] = "medium"
    rec_flags["issue_description"] = rec_flags["recommended_treatment"]
    rec_flags["recommended_fix"] = rec_flags["hard_gates_triggered"]
    rec_flags["model_impact"] = rec_flags["reason_codes"]
    rec_flags["source_file"] = ""
    rec_flags["source_row"] = ""
    rec_flags["resolved_flag"] = False
    rec_flags["date_logged"] = ""
    rec_flags = rec_flags[severe_issues.columns] if not severe_issues.empty else rec_flags
    return pd.concat([severe_issues, rec_flags], ignore_index=True)


def build_summary(
    zones: pd.DataFrame,
    issues: pd.DataFrame,
    contradictions: pd.DataFrame,
    confidence: pd.DataFrame,
    activity: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "version": "v0.5-lite",
        "title": "v0.5-lite - SEZ Zone Triage and Calibration Support MVP",
        "zone_records_loaded": int(len(zones)),
        "detected_zone_profile_records_from_source_digest": 35,
        "normalized_indicator_records_from_source_digest": 35,
        "demo_data_used": False,
        "demo_data_created": False,
        "placeholders_created": False,
        "dataset_scope_note": "The source digest reports 35 detected zone profile records and 35 normalized indicator records. Exact row-level verification should use the original workbook.",
        "data_quality_issue_count": int(len(issues)),
        "contradiction_count": int(len(contradictions)),
        "confidence_band_counts": confidence["data_confidence_band"].value_counts().to_dict(),
        "activity_category_counts": activity["activity_category"].value_counts().to_dict(),
        "possible_pilot_screen_candidates": int(recommendations["possible_screen_candidate_flag"].astype(bool).sum()),
        "more_data_required": int(recommendations["recommended_treatment"].astype(str).str.contains("More data required", case=False, na=False).sum()),
        "legal_review_required_or_placeholder": int(recommendations["required_legal_action"].astype(str).str.contains("legal", case=False, na=False).sum()),
        "recommendation_count": int(len(recommendations)),
        "outputs": REQUIRED_OUTPUTS,
        "limitations": [
            "Recommendations are provisional and demo-only.",
            "Legal fields are placeholders pending D4 legal review.",
            "Fiscal fields are placeholders pending D5/FBR/customs verification.",
            "The current normalized data is the 35-zone demo dataset, not the final reconciled 44/54-zone universe.",
            "Any support-related output is subject to D4 legal review and D5 fiscal verification.",
            "Cost-based support language means temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.",
            "No tax rates or incentive awards are calculated.",
        ],
    }


def export_excel(path: Path, summary: dict[str, Any], frames: dict[str, pd.DataFrame], reason_codes: dict[str, str]) -> None:
    ensure_dir(path.parent)
    summary_df = pd.DataFrame([{"metric": key, "value": _summary_value(value)} for key, value in summary.items()])
    reason_df = pd.DataFrame([{"reason_code": key, "reason_text": value} for key, value in reason_codes.items()])
    limitations_df = pd.DataFrame(
        {
            "limitation": [
                "Legal fields are placeholders pending D4 legal review.",
                "Fiscal exposure fields are placeholders pending D5/FBR/customs verification.",
                "Enterprise and plot-level data are not yet fully loaded.",
                "The normalized dataset covers 35 detected zone profile records and 35 normalized indicator records based on the source digest.",
                "The current normalized data is the 35-zone demo dataset, not the final reconciled 44/54-zone universe.",
                "Exact row-level verification should use the original workbook.",
                "Recommendations are provisional and for demonstration only.",
                "Any support-related output is subject to D4 legal review and D5 fiscal verification.",
                "Cost-based support language means temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.",
                "No tax rates or incentive awards are calculated.",
                "Human review is mandatory.",
            ]
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="00_summary", index=False)
        frames["recommendations"].to_excel(writer, sheet_name="01_zone_triage", index=False)
        frames["explanations"].to_excel(writer, sheet_name="02_recommendation_explanations", index=False)
        frames["issues"].to_excel(writer, sheet_name="03_data_quality_issues", index=False)
        frames["contradictions"].to_excel(writer, sheet_name="04_contradictions", index=False)
        frames["confidence"].to_excel(writer, sheet_name="05_data_confidence", index=False)
        frames["activity"].to_excel(writer, sheet_name="06_activity_classification", index=False)
        reason_df.to_excel(writer, sheet_name="07_reason_codes", index=False)
        frames["legal"].to_excel(writer, sheet_name="08_legal_placeholders", index=False)
        frames["fiscal"].to_excel(writer, sheet_name="09_fiscal_placeholders", index=False)
        limitations_df.to_excel(writer, sheet_name="10_limitations", index=False)

        workbook = writer.book
        for worksheet in workbook.worksheets:
            worksheet.freeze_panes = "A2"
            if worksheet.max_row > 1 and worksheet.max_column > 1:
                worksheet.auto_filter.ref = worksheet.dimensions
            for column_cells in worksheet.columns:
                letter = column_cells[0].column_letter
                max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells[:100])
                worksheet.column_dimensions[letter].width = min(max(max_length + 2, 12), 48)


def _summary_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)
