"""日度 IC 时间序列。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from scripts.qlib.viz.plots.common import prepare_daily_series, save_figure


def plot_ic_line(raw: Any, path: Path) -> Path | None:
    v = prepare_daily_series(raw)
    if v is None or v.empty:
        return None
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(v.index, v.values, linewidth=1.0)
    ax.set_title("IC (SigAnaRecord)")
    ax.set_xlabel("Date")
    ax.set_ylabel("IC")
    ax.axhline(0.0, color="gray", linewidth=0.8, linestyle="--")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    save_figure(fig, path)
    return path
