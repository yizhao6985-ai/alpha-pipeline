"""策略回撤曲线。"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from scripts.qlib.viz.plots.common import save_figure
from scripts.qlib.viz.plots.portfolio_common import ensure_datetime_index


def plot_portfolio_drawdown(report: pd.DataFrame, path: Path) -> None:
    rep = ensure_datetime_index(report)
    r = pd.to_numeric(rep["return"], errors="coerce").fillna(0.0)
    eq = r.cumsum()
    dd = eq - eq.cummax()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dd.index, dd.values, label="Strategy Drawdown", color="C3", linewidth=1.0)
    ax.set_title("Drawdown")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, path)
