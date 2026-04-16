"""策略与基准累计收益曲线。"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.qlib.viz.plots.common import save_figure
from scripts.qlib.viz.plots.portfolio_common import ensure_datetime_index


def plot_portfolio_cumulative_return(report: pd.DataFrame, path: Path) -> None:
    rep = ensure_datetime_index(report)
    r = pd.to_numeric(rep["return"], errors="coerce").fillna(0.0)
    b = pd.to_numeric(rep["bench"], errors="coerce").fillna(0.0)
    cum_r = r.cumsum()
    cum_b = b.cumsum()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(cum_r.index, cum_r.values, label="Strategy", linewidth=1.2)
    ax.plot(cum_b.index, cum_b.values, label="Benchmark", linewidth=1.0, alpha=0.85)
    ax.set_title("Cumulative Return")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Return")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, path)
