from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from sez_calibration.export_outputs import run_pipeline  # noqa: E402


def main() -> None:
    result = run_pipeline(ROOT)
    summary = result["summary"]
    output_dir = result["output_dir"]
    confidence_counts = summary["confidence_band_counts"]
    activity_counts = summary["activity_category_counts"]

    print("SEZ Calibration Demo Summary")
    print(f"Data profile: {summary.get('data_profile', 'source')}")
    print(f"Synthetic demo data used: {summary.get('synthetic_demo_data_used', False)}")
    print(f"Zones loaded: {summary['zone_records_loaded']}")
    print(f"Demo data used: {summary['demo_data_used']}")
    print(f"Placeholders created: {summary['placeholders_created']}")
    print(f"Validation flags: {summary['data_quality_issue_count']}")
    print(f"Cross-source/status conflicts: {summary['contradiction_count']}")
    print(f"Recommendation records: {summary['recommendation_count']}")
    print(f"D6 model version: {summary.get('fiscal_model_version', 'not available')}")
    print(f"D6 calibration status: {summary.get('calibration_status', 'not available')}")
    print(f"D6 synthetic model-ready enterprise records: {summary.get('calibration_model_ready_enterprise_count', 0)}")
    print("Confidence bands:")
    for band in ["high", "medium", "low", "do_not_use"]:
        print(f"  {band}: {confidence_counts.get(band, 0)}")
    print("Activity categories:")
    for category in ["reported_operating_activity", "moving_toward_production", "allotted_but_inactive", "vacant_or_speculative", "unclear"]:
        print(f"  {category}: {activity_counts.get(category, 0)}")
    print("Core outputs:")
    for name in [
        "data_quality_issue_log.csv",
        "contradiction_log.csv",
        "data_confidence_scores.csv",
        "activity_classification.csv",
        "calibration_portfolio_summary.csv",
        "calibration_parameter_ranges.csv",
        "calibration_d7_handoff.csv",
    ]:
        print(f"  {output_dir / name}")


if __name__ == "__main__":
    main()
