from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .calibration_model import MODEL_VERSION as CALIBRATION_MODEL_VERSION
from .calibration_model import run_calibration_model
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
    "calibration_enterprise_inputs.csv",
    "calibration_scenario_definitions.csv",
    "calibration_model_readiness.csv",
    "calibration_input_register.csv",
    "calibration_run_manifest.csv",
    "calibration_excluded_records.csv",
    "calibration_annual_enterprise.csv",
    "calibration_zone_aggregation.csv",
    "calibration_portfolio_summary.csv",
    "calibration_sensitivity.csv",
    "calibration_parameter_ranges.csv",
    "calibration_assumptions.csv",
    "calibration_verification_rules.csv",
    "calibration_reconciliation.csv",
    "calibration_d7_handoff.csv",
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
    profile_data_dir = Path(str(ingest_metadata.get("data_profile_dir", data_dir)))
    legal, fiscal, placeholder_metadata = ensure_placeholder_tables_with_metadata(zones, profile_data_dir)
    issues, contradictions, field_completeness = run_data_quality_checks(zones)
    consistency_inputs = pd.concat([issues, contradictions], ignore_index=True)
    confidence = calculate_confidence_scores(zones, consistency_inputs)
    activity = classify_activity(zones)
    recommendations = run_recommendation_engine(zones, confidence, activity, legal, fiscal, issues, scenario)
    calibration_frames = run_calibration_model(
        root,
        zones,
        recommendations,
        data_profile=str(ingest_metadata.get("data_profile", "synthetic")),
        scenario=scenario,
    )
    calibration_frames["calibration_run_manifest"] = build_run_manifest(
        root,
        profile_data_dir,
        ingest_metadata,
        scenario or {},
    )
    reason_codes = load_reason_codes(config_dir / "reason_codes_v0_5_lite.yaml")
    explanations = build_recommendation_explanations(recommendations, reason_codes)
    audit_flags = build_audit_flags(issues, contradictions, recommendations)
    summary = build_summary(zones, issues, contradictions, confidence, activity, recommendations, calibration_frames)
    summary.update(ingest_metadata)
    summary.update(placeholder_metadata)
    summary = _relativize_summary_paths(summary, root)
    if summary.get("data_profile") == "synthetic":
        summary["title"] = "SEZ D6 Calibration Workbench"
        summary["dataset_scope_note"] = (
            "Default public demo uses fully synthetic hypothetical-zone records. Real policy use requires "
            "validated BOI/SEZA source records, D4 legal review, D5/FBR fiscal verification, enterprise-level data, "
            "KPI validation, and additionality/counterfactual analysis."
        )
        summary["detected_zone_profile_records_from_source_digest"] = int(len(zones))
        summary["normalized_indicator_records_from_source_digest"] = int(len(zones))
        summary["limitations"] = [
            "Default public demo uses fully synthetic hypothetical-zone records.",
            "Outputs are provisional screening outputs for human review.",
            "Outputs do not approve incentives, set final tax rates, determine final validated fiscal cost, or replace BOI, FBR, Finance Division, SEZA, Law Division, IMF, programme, fiscal modeller, or legal counsel review.",
            "Real policy use requires validated BOI/SEZA source records, D4 legal review, D5/FBR fiscal verification, enterprise-level data, KPI validation, and additionality/counterfactual analysis.",
            "Cost-based support language means temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.",
        ]

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
    frames.update(calibration_frames)

    if write_outputs:
        write_csv(recommendations, output_dir / "zone_triage_prototype.csv")
        write_csv(explanations, output_dir / "recommendation_explanations.csv")
        write_csv(audit_flags, output_dir / "audit_flags.csv")
        write_csv(issues, output_dir / "data_quality_issue_log.csv")
        write_csv(contradictions, output_dir / "contradiction_log.csv")
        write_csv(confidence, output_dir / "data_confidence_scores.csv")
        write_csv(activity, output_dir / "activity_classification.csv")
        write_csv(field_completeness, output_dir / "field_completeness.csv")
        write_csv(frames["calibration_enterprise_inputs"], output_dir / "calibration_enterprise_inputs.csv")
        write_csv(frames["calibration_scenario_definitions"], output_dir / "calibration_scenario_definitions.csv")
        write_csv(frames["calibration_model_readiness"], output_dir / "calibration_model_readiness.csv")
        write_csv(frames["calibration_input_register"], output_dir / "calibration_input_register.csv")
        write_csv(frames["calibration_run_manifest"], output_dir / "calibration_run_manifest.csv")
        write_csv(frames["calibration_excluded_records"], output_dir / "calibration_excluded_records.csv")
        write_csv(frames["calibration_annual_enterprise"], output_dir / "calibration_annual_enterprise.csv")
        write_csv(frames["calibration_zone_aggregation"], output_dir / "calibration_zone_aggregation.csv")
        write_csv(frames["calibration_portfolio_summary"], output_dir / "calibration_portfolio_summary.csv")
        write_csv(frames["calibration_sensitivity"], output_dir / "calibration_sensitivity.csv")
        write_csv(frames["calibration_parameter_ranges"], output_dir / "calibration_parameter_ranges.csv")
        write_csv(frames["calibration_assumptions"], output_dir / "calibration_assumptions.csv")
        write_csv(frames["calibration_verification_rules"], output_dir / "calibration_verification_rules.csv")
        write_csv(frames["calibration_reconciliation"], output_dir / "calibration_reconciliation.csv")
        write_csv(frames["calibration_d7_handoff"], output_dir / "calibration_d7_handoff.csv")
        write_json(summary, output_dir / "summary.json")
        export_excel(output_dir / "sez_calibration_demo_outputs.xlsx", summary, frames, reason_codes)

    return {"summary": summary, "frames": frames, "output_dir": output_dir}


def build_run_manifest(
    root: Path,
    profile_data_dir: Path,
    ingest_metadata: dict[str, Any],
    scenario: dict[str, Any],
) -> pd.DataFrame:
    input_path = Path(str(ingest_metadata.get("input_file", "")))
    files = {
        "zone_data": input_path,
        "legal_fiscal": profile_data_dir / "legal_fiscal_placeholders.csv",
        "enterprise_data": profile_data_dir / "synthetic_enterprise_summary.csv",
        "sample_weights": profile_data_dir / "synthetic_enterprise_weights.csv",
        "assumptions": profile_data_dir / "synthetic_calibration_assumptions.csv",
        "verification_rules": profile_data_dir / "synthetic_verification_requirements.csv",
        "reason_codes": root / "config" / "reason_codes_v0_5_lite.yaml",
        "input_requirements": root / "config" / "d6_input_requirements_v0_1.csv",
        "model_code": root / "src" / "sez_calibration" / "calibration_model.py",
    }
    hashes = {name: _sha256_file(path) for name, path in files.items()}
    scenario_hash = hashlib.sha256(
        json.dumps(scenario, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    run_hash = _combined_hash([*hashes.values(), scenario_hash, CALIBRATION_MODEL_VERSION])
    source_manifest = " | ".join(f"{name}:{value[:12]}" for name, value in hashes.items())
    return pd.DataFrame(
        [
            {
                "run_id": f"RUN-{run_hash[:16].upper()}",
                "data_snapshot_id": f"DATA-{_combined_hash([hashes['zone_data'], hashes['enterprise_data']])[:16].upper()}",
                "legal_snapshot_id": f"LEGAL-{hashes['legal_fiscal'][:16].upper()}",
                "assumption_set_id": f"ASSUMP-{hashes['assumptions'][:16].upper()}",
                "sample_weight_version": f"WEIGHT-{hashes['sample_weights'][:16].upper()}",
                "ruleset_version": f"RULE-{_combined_hash([hashes['reason_codes'], hashes['verification_rules']])[:16].upper()}",
                "input_requirement_version": f"INPUT-{hashes['input_requirements'][:16].upper()}",
                "model_version": CALIBRATION_MODEL_VERSION,
                "model_code_hash": hashes["model_code"],
                "scenario_override_hash": scenario_hash,
                "data_profile": str(ingest_metadata.get("data_profile", "synthetic")),
                "data_state": "STANDARDIZED synthetic observations; not VALIDATED",
                "model_qa_state": "Generated; independent model validation pending",
                "approval_state": "NOT_SUBMITTED - human review required",
                "publication_state": "SYNTHETIC_DEMO_ONLY",
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_manifest": source_manifest,
            }
        ]
    )


def _sha256_file(path: Path) -> str:
    if not path or not path.exists() or not path.is_file():
        return hashlib.sha256(b"missing").hexdigest()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _combined_hash(parts: list[str]) -> str:
    payload = "|".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    calibration_frames: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    calibration_frames = calibration_frames or {}
    portfolio = calibration_frames.get("calibration_portfolio_summary", pd.DataFrame())
    readiness = calibration_frames.get("calibration_model_readiness", pd.DataFrame())
    annual = calibration_frames.get("calibration_annual_enterprise", pd.DataFrame())
    parameter_ranges = calibration_frames.get("calibration_parameter_ranges", pd.DataFrame())
    run_manifest = calibration_frames.get("calibration_run_manifest", pd.DataFrame())
    model_ready_count = 0
    if not readiness.empty and "model_ready" in readiness.columns:
        model_ready_count = int(readiness["model_ready"].astype(bool).sum())
    calibration_status = "blocked"
    if not annual.empty:
        calibration_status = "calculated_for_synthetic_model_ready_enterprise_records"
    elif not portfolio.empty and "calibration_status" in portfolio.columns:
        calibration_status = str(portfolio["calibration_status"].iloc[0])
    return {
        "version": "v0.5-lite",
        "fiscal_model_version": CALIBRATION_MODEL_VERSION,
        "calibration_status": calibration_status,
        "calibration_model_ready_enterprise_count": model_ready_count,
        "calibration_enterprise_record_count": int(len(readiness)) if not readiness.empty else 0,
        "calibration_annual_row_count": int(len(annual)),
        "calibration_scenario_count": int(portfolio["scenario_id"].nunique()) if not portfolio.empty and "scenario_id" in portfolio.columns else 0,
        "calibration_parameter_range_count": int(len(parameter_ranges)),
        "calibration_run_id": (
            str(run_manifest["run_id"].iloc[0])
            if not run_manifest.empty and "run_id" in run_manifest.columns
            else "Not generated"
        ),
        "title": "SEZ D6 Calibration Workbench",
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
            "The current public demo uses 14 fully synthetic hypothetical-zone records. Do not generalize to Pakistan's full SEZ/EPZ universe without BOI/SEZA/FBR/legal reconciliation.",
            "Any support-related output is subject to D4 legal review and D5 fiscal verification.",
            "Cost-based support language means temporary transition support only; all SEZ fiscal incentives phase out by 30 June 2035.",
            "No final tax rates or incentive awards are calculated.",
        ],
    }


def export_excel(path: Path, summary: dict[str, Any], frames: dict[str, pd.DataFrame], reason_codes: dict[str, str]) -> None:
    ensure_dir(path.parent)
    summary_df = pd.DataFrame([{"metric": key, "value": _summary_value(value)} for key, value in summary.items()])
    reason_df = pd.DataFrame([{"reason_code": key, "reason_text": value} for key, value in reason_codes.items()])
    limitations_df = pd.DataFrame({"limitation": summary.get("limitations", [])})
    read_me = pd.DataFrame(
        [
            {
                "item": "Workbook purpose",
                "detail": "Synthetic D6 calibration-analysis review package for workflow demonstration only.",
            },
            {
                "item": "Decision status",
                "detail": "Does not approve incentives, set tax rates, determine final fiscal cost, or replace D4/D5/human review.",
            },
            {
                "item": "Model version",
                "detail": summary.get("fiscal_model_version", CALIBRATION_MODEL_VERSION),
            },
            {
                "item": "Dataset basis",
                "detail": "Structured screening dataset; current demo is synthetic and not the final reconciled 44/54-zone universe.",
            },
        ]
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        read_me.to_excel(writer, sheet_name="00_read_me", index=False)
        frames.get("calibration_input_register", pd.DataFrame()).to_excel(writer, sheet_name="01_input_register", index=False)
        frames.get("calibration_run_manifest", pd.DataFrame()).to_excel(writer, sheet_name="02_run_manifest", index=False)
        frames.get("calibration_enterprise_inputs", pd.DataFrame()).to_excel(writer, sheet_name="01_raw_enterprise_inputs", index=False)
        frames.get("calibration_assumptions", pd.DataFrame()).to_excel(writer, sheet_name="02_model_assumptions", index=False)
        frames.get("calibration_scenario_definitions", pd.DataFrame()).to_excel(writer, sheet_name="03_scenario_definitions", index=False)
        frames.get("calibration_annual_enterprise", pd.DataFrame()).to_excel(writer, sheet_name="04_annual_enterprise", index=False)
        frames.get("calibration_zone_aggregation", pd.DataFrame()).to_excel(writer, sheet_name="05_zone_aggregation", index=False)
        frames.get("calibration_portfolio_summary", pd.DataFrame()).to_excel(writer, sheet_name="06_portfolio_summary", index=False)
        frames.get("calibration_sensitivity", pd.DataFrame()).to_excel(writer, sheet_name="07_sensitivity", index=False)
        frames.get("calibration_parameter_ranges", pd.DataFrame()).to_excel(writer, sheet_name="08_parameter_ranges", index=False)
        frames.get("calibration_verification_rules", pd.DataFrame()).to_excel(writer, sheet_name="09_verification_rules", index=False)
        frames["recommendations"].to_excel(writer, sheet_name="10_readiness_triage", index=False)
        frames["explanations"].to_excel(writer, sheet_name="11_pathway_rationale", index=False)
        frames["audit_flags"].to_excel(writer, sheet_name="12_validation_flags", index=False)
        frames.get("calibration_reconciliation", pd.DataFrame()).to_excel(writer, sheet_name="13_reconciliation", index=False)
        frames.get("calibration_d7_handoff", pd.DataFrame()).to_excel(writer, sheet_name="14_d7_handoff", index=False)
        summary_df.to_excel(writer, sheet_name="15_summary_metadata", index=False)
        reason_df.to_excel(writer, sheet_name="16_reason_codes", index=False)
        frames["issues"].to_excel(writer, sheet_name="17_source_flags", index=False)
        frames["contradictions"].to_excel(writer, sheet_name="18_consistency_flags", index=False)
        frames["confidence"].to_excel(writer, sheet_name="19_record_quality", index=False)
        frames["activity"].to_excel(writer, sheet_name="20_activity_classification", index=False)
        limitations_df.to_excel(writer, sheet_name="21_limitations", index=False)

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


def _relativize_summary_paths(summary: dict[str, Any], root: Path) -> dict[str, Any]:
    out = dict(summary)
    for key in ["data_profile_dir", "input_file", "placeholder_file"]:
        value = out.get(key)
        if not value:
            continue
        try:
            out[key] = str(Path(str(value)).resolve().relative_to(root.resolve())).replace("\\", "/")
        except (OSError, ValueError):
            out[key] = Path(str(value)).name
    return out
