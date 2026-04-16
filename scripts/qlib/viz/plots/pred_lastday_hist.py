"""预测最后交易日截面分布直方图。"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.qlib.viz.plots.common import save_figure, score_column


def plot_pred_lastday_hist(pred: pd.DataFrame, path: Path) -> Path | None:
    if pred is None or pred.empty or not isinstance(pred, pd.DataFrame):
        return None
    col = score_column(pred)
    if isinstance(pred.index, pd.MultiIndex):
        dt = pred.index.get_level_values(0)
        last = pd.Timestamp(dt.max())
        sub = pred.loc[dt == last, col]
    else:
        sub = pred[col]
    sub = pd.to_numeric(sub, errors="coerce").dropna()
    if sub.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(sub.values, bins=min(50, max(10, len(sub) // 20)), color="C0", alpha=0.85)
    ax.set_title("Prediction score distribution (last day, pred.pkl)")
    ax.set_xlabel("Score")
    ax.set_ylabel("Count")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, path)
    return path
