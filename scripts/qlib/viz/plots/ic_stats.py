"""IC / Rank IC 类日度序列的常规统计，写入 CSV。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.qlib.viz.plots.common import prepare_daily_series


def summarize_ic_like_series(raw: Any, *, annualization: int = 252) -> dict[str, float | int] | None:
    """日度 IC 常用指标：均值、标准差、年化 IR、正率、t 统计量、最值、样本数。"""
    v = prepare_daily_series(raw)
    if v is None or v.empty:
        return None
    n = int(len(v))
    mean = float(v.mean())
    std = float(v.std(ddof=1)) if n > 1 else 0.0
    ir_ann = float(mean / std * np.sqrt(annualization)) if std > 1e-12 else float("nan")
    pos_rate = float((v > 0).mean())
    t_stat = float(mean / (std / np.sqrt(n))) if std > 1e-12 else float("nan")
    return {
        "n_days": n,
        "mean": mean,
        "std": std,
        "ir_ann": ir_ann,
        "positive_rate": pos_rate,
        "t_stat": t_stat,
        "min": float(v.min()),
        "max": float(v.max()),
    }


def write_ic_like_stats_csv(raw: Any, path: Path, *, annualization: int = 252) -> Path | None:
    stats = summarize_ic_like_series(raw, annualization=annualization)
    if stats is None:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([stats]).to_csv(path, index=False)
    return path
