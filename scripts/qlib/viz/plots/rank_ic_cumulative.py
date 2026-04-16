"""日度 Rank IC 累积和。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from scripts.qlib.viz.plots.common import prepare_daily_series, save_figure


def plot_rank_ic_cumulative(raw: Any, path: Path) -> Path | None:
    v = prepare_daily_series(raw)
    if v is None or v.empty:
        return None
    cum = v.cumsum()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(cum.index, cum.values, linewidth=1.0, color="C2")
    ax.set_title("Cumulative Rank IC (sum of daily Rank IC)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative Rank IC")
    ax.axhline(0.0, color="gray", linewidth=0.8, linestyle="--")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, path)
    return path
