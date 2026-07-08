from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sez_calibration.export_outputs import REQUIRED_OUTPUTS, run_pipeline
from sez_calibration.ingest import load_zone_data_with_metadata


REAL_ZONE_NAME_FRAGMENTS = [
    "Rashakai",
    "Allama Iqbal",
    "M3",
    "Bin Qasim",
    "Khairpur",
    "Hattar",
    "Dhabeji",
    "Bostan",
]


def copy_synthetic_project(tmp_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    shutil.copytree(repo_root / "config", tmp_path / "config")
    shutil.copytree(repo_root / "data" / "synthetic", tmp_path / "data" / "synthetic")
    return tmp_path


def test_synthetic_demo_files_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    synthetic_dir = repo_root / "data" / "synthetic"
    assert (synthetic_dir / "SEZ_Key_Indicators_Normalized.csv").exists()
    assert (synthetic_dir / "legal_fiscal_placeholders.csv").exists()


def test_default_profile_is_synthetic(monkeypatch) -> None:
    monkeypatch.delenv("SEZ_DATA_PROFILE", raising=False)
    repo_root = Path(__file__).resolve().parents[1]
    zones, metadata = load_zone_data_with_metadata(repo_root / "data")

    assert metadata["data_profile"] == "synthetic"
    assert metadata["synthetic_demo_data_used"] is True
    assert len(zones) >= 10
    assert zones["zone_id"].astype(str).str.startswith("SYN-").any()


def test_synthetic_demo_has_diverse_pathways(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SEZ_DATA_PROFILE", raising=False)
    project_root = copy_synthetic_project(tmp_path)
    result = run_pipeline(project_root, write_outputs=True)
    recommendations = result["frames"]["recommendations"]
    treatments = recommendations["recommended_treatment"].astype(str)
    treatment_text = " | ".join(treatments)

    assert treatments.nunique() >= 4
    for expected in [
        "Legal review required",
        "More data required",
        "Sanction / withdrawal review",
        "Potential pilot-review flag",
    ]:
        assert expected in treatment_text


def test_synthetic_demo_does_not_use_real_zone_names(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SEZ_DATA_PROFILE", raising=False)
    project_root = copy_synthetic_project(tmp_path)
    result = run_pipeline(project_root, write_outputs=False)
    zone_names = " | ".join(result["frames"]["zones"]["zone_name"].astype(str))

    for fragment in REAL_ZONE_NAME_FRAGMENTS:
        assert fragment.lower() not in zone_names.lower()


def test_exports_created_from_synthetic_profile(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("SEZ_DATA_PROFILE", raising=False)
    project_root = copy_synthetic_project(tmp_path)
    result = run_pipeline(project_root)
    output_dir = result["output_dir"]

    assert result["summary"]["data_profile"] == "synthetic"
    assert result["summary"]["synthetic_demo_data_used"] is True
    for name in REQUIRED_OUTPUTS:
        path = output_dir / name
        assert path.exists(), name
        assert path.stat().st_size > 0, name
    assert (output_dir / "sez_calibration_demo_outputs.xlsx").exists()
