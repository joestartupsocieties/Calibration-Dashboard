from __future__ import annotations

from pathlib import Path

import pandas as pd

from .normalize import normalize_columns, sample_zone_rows
from .utils import ensure_dir


DEFAULT_INPUT_FILE = "SEZ_Key_Indicators_Normalized.csv"


def load_zone_data(data_dir: Path) -> pd.DataFrame:
    ensure_dir(data_dir)
    path = data_dir / DEFAULT_INPUT_FILE
    if not path.exists():
        sample = pd.DataFrame(sample_zone_rows())
        sample.to_csv(path, index=False, encoding="utf-8")
    raw = pd.read_csv(path, encoding="utf-8-sig")
    return normalize_columns(raw)
