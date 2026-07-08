from __future__ import annotations

import shutil
from pathlib import Path

from sez_calibration.export_outputs import REQUIRED_OUTPUTS, run_pipeline


def test_run_demo_creates_required_outputs(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp_path / "config")
    result = run_pipeline(tmp_path)
    output_dir = result["output_dir"]
    for name in REQUIRED_OUTPUTS:
        assert (output_dir / name).exists(), name


def test_output_csvs_are_non_empty_when_input_is_non_empty(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp_path / "config")
    result = run_pipeline(tmp_path)
    output_dir = result["output_dir"]
    for name in [
        "zone_triage_prototype.csv",
        "recommendation_explanations.csv",
        "audit_flags.csv",
        "data_quality_issue_log.csv",
        "contradiction_log.csv",
        "data_confidence_scores.csv",
        "activity_classification.csv",
    ]:
        assert (output_dir / name).stat().st_size > 0
