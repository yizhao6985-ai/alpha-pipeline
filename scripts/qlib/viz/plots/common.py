"""绘图共用：后端、序列规范化、保存。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def score_column(pred: pd.DataFrame) -> str:
    if pred.empty:
        return "score"
    return str(pred.columns[0])


def prepare_daily_series(raw: Any) -> pd.Series | None:
    """将 recorder 中的 ic/ric 等转为按日 ``Series``（数值、dropna、尽量 DatetimeIndex）。"""
    if raw is None:
        return None
    if isinstance(raw, pd.DataFrame):
        if raw.empty or len(raw.columns) == 0:
            return None
        s = pd.to_numeric(raw.iloc[:, 0], errors="coerce")
        idx = raw.index
    elif isinstance(raw, pd.Series):
        s = pd.to_numeric(raw, errors="coerce")
        idx = raw.index
    else:
        return None
    v = pd.Series(np.asarray(s), index=idx).dropna()
    if v.empty:
        return None
    if not isinstance(v.index, pd.DatetimeIndex):
        try:
            v.index = pd.to_datetime(v.index, errors="coerce")
            v = v[v.index.notna()].sort_index()
        except Exception:  # noqa: BLE001
            pass
    if v.empty:
        return None
    return v


def save_figure(fig: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
