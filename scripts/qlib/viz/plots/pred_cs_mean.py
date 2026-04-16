"""预测截面均值时间序列。"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.qlib.viz.plots.common import save_figure, score_column


def plot_pred_cross_sectional_mean(pred: pd.DataFrame, path: Path) -> Path | None:
    if pred is None or pred.empty or not isinstance(pred, pd.DataFrame):
        return None
    col = score_column(pred)
    s = pd.to_numeric(pred[col], errors="coerce")
    if isinstance(pred.index, pd.MultiIndex):
        dt = pred.index.get_level_values(0)
        g = s.groupby(dt).mean().sort_index()
    else:
        g = s
    if g.empty:
        return None
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(g.index, g.values, linewidth=1.0, color="C0")
    ax.set_title("Prediction: cross-sectional mean (SignalRecord pred.pkl)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Mean score")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, path)
    return path
