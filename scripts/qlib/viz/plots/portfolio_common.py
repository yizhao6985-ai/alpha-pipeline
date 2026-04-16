"""组合报表 DataFrame 预处理。"""
from __future__ import annotations

import pandas as pd


def ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, errors="coerce")
    return out.sort_index()
