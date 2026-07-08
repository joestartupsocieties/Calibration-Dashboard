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
    print(f"Loaded {summary['zone_records_loaded']} zones.")
    print(f"Logged {summary['data_quality_issue_count']} data-quality issues.")
    print(f"Logged {summary['contradiction_count']} contradiction/source-scope flags.")
    print(f"Generated {summary['zone_records_loaded']} confidence scores.")
    print(f"Generated {summary['recommendation_count']} provisional recommendations.")
    print(f"Possible pilot screen candidates: {summary['possible_pilot_screen_candidates']}.")
    print(f"More data required: {summary['more_data_required']}.")
    print(f"Legal review required or placeholder: {summary['legal_review_required_or_placeholder']}.")
    print(f"Outputs written to {output_dir}.")


if __name__ == "__main__":
    main()
