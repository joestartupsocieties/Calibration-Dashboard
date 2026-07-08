from __future__ import annotations

from pathlib import Path

import pandas as pd

from .normalize import normalize_columns, sample_zone_rows
from .utils import ensure_dir


DEFAULT_INPUT_FILE = "SEZ_Key_Indicators_Normalized.csv"


def load_zone_data(data_dir: Path) -> pd.DataFrame:
    data, _metadata = load_zone_data_with_metadata(data_dir)
    return data


def load_zone_data_with_metadata(data_dir: Path) -> tuple[pd.DataFrame, dict[str, object]]:
    ensure_dir(data_dir)
    path = data_dir / DEFAULT_INPUT_FILE
    demo_data_created = False
    if not path.exists():
        sample = pd.DataFrame(sample_zone_rows())
        sample.to_csv(path, index=False, encoding="utf-8")
        demo_data_created = True
    raw = pd.read_csv(path, encoding="utf-8-sig")
    normalized = normalize_columns(raw)
    demo_data_used = demo_data_created or _looks_like_demo_data(normalized)
    metadata = {
        "input_file": str(path),
        "demo_data_used": bool(demo_data_used),
        "demo_data_created": bool(demo_data_created),
    }
    return normalized, metadata


def _looks_like_demo_data(df: pd.DataFrame) -> bool:
    if "demo_data_flag" in df.columns:
        return df["demo_data_flag"].fillna(False).astype(str).str.lower().isin(["true", "1", "yes"]).any()
    if "source_file" in df.columns:
        return df["source_file"].fillna("").astype(str).str.contains("generated_demo_sample", case=False, na=False).any()
    return False
