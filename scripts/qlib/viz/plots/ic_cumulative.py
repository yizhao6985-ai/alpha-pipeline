"""日度 IC 累积和（观察累计预测力）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from scripts.qlib.viz.plots.common import prepare_daily_series, save_figure


def plot_ic_cumulative(raw: Any, path: Path) -> Path | None:
    v = prepare_daily_series(raw)
    if v is None or v.empty:
        return None
    cum = v.cumsum()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(cum.index, cum.values, linewidth=1.0, color="C2")
    ax.set_title("Cumulative IC (sum of daily IC)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative IC")
    ax.axhline(0.0, color="gray", linewidth=0.8, linestyle="--")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, path)
    return path
