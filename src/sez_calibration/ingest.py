from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from .normalize import normalize_columns, sample_zone_rows
from .utils import ensure_dir


DEFAULT_INPUT_FILE = "SEZ_Key_Indicators_Normalized.csv"
DATA_PROFILE_ENV_VAR = "SEZ_DATA_PROFILE"
DEFAULT_DATA_PROFILE = "synthetic"
SUPPORTED_DATA_PROFILES = {"synthetic", "source"}


def active_data_profile(profile: str | None = None) -> str:
    selected = (profile or os.getenv(DATA_PROFILE_ENV_VAR) or DEFAULT_DATA_PROFILE).strip().lower()
    if selected not in SUPPORTED_DATA_PROFILES:
        raise ValueError(
            f"Unsupported SEZ data profile '{selected}'. Use one of: {', '.join(sorted(SUPPORTED_DATA_PROFILES))}."
        )
    return selected


def profile_data_dir(data_dir: Path, profile: str | None = None) -> Path:
    selected = active_data_profile(profile)
    return data_dir / "synthetic" if selected == "synthetic" else data_dir


def load_zone_data(data_dir: Path, profile: str | None = None) -> pd.DataFrame:
    data, _metadata = load_zone_data_with_metadata(data_dir, profile=profile)
    return data


def load_zone_data_with_metadata(data_dir: Path, profile: str | None = None) -> tuple[pd.DataFrame, dict[str, object]]:
    ensure_dir(data_dir)
    selected_profile = active_data_profile(profile)
    selected_data_dir = ensure_dir(profile_data_dir(data_dir, selected_profile))
    path = selected_data_dir / DEFAULT_INPUT_FILE
    demo_data_created = False
    synthetic_source_file_found = path.exists()
    if not path.exists():
        sample = pd.DataFrame(sample_zone_rows())
        sample.to_csv(path, index=False, encoding="utf-8")
        demo_data_created = True
    raw = pd.read_csv(path, encoding="utf-8-sig")
    normalized = normalize_columns(raw)
    demo_data_used = demo_data_created or _looks_like_demo_data(normalized)
    metadata = {
        "data_profile": selected_profile,
        "data_profile_dir": str(selected_data_dir),
        "input_file": str(path),
        "demo_data_used": bool(demo_data_used),
        "demo_data_created": bool(demo_data_created),
        "synthetic_demo_data_used": bool(selected_profile == "synthetic" and not demo_data_created),
        "synthetic_demo_data_missing": bool(selected_profile == "synthetic" and not synthetic_source_file_found),
    }
    if selected_profile == "synthetic" and not synthetic_source_file_found:
        metadata["data_profile_warning"] = (
            "Synthetic demo data file was not found; generated fallback demo data in data/synthetic/."
        )
    return normalized, metadata


def _looks_like_demo_data(df: pd.DataFrame) -> bool:
    if "demo_data_flag" in df.columns:
        return df["demo_data_flag"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"]).any()
    if "source_file" in df.columns:
        return df["source_file"].fillna("").astype(str).str.contains("generated_demo_sample", case=False, na=False).any()
    return False
