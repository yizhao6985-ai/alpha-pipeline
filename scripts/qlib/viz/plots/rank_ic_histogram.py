"""日度 Rank IC 分布直方图。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from scripts.qlib.viz.plots.common import prepare_daily_series, save_figure


def plot_rank_ic_histogram(raw: Any, path: Path) -> Path | None:
    v = prepare_daily_series(raw)
    if v is None or v.empty:
        return None
    arr = v.values.astype(float)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(arr, bins=min(50, max(10, len(arr) // 20)), color="C1", alpha=0.85)
    ax.axvline(float(np.nanmean(arr)), color="C3", linewidth=1.2, label=f"mean={np.nanmean(arr):.4f}")
    ax.set_title("Rank IC distribution (daily)")
    ax.set_xlabel("Rank IC")
    ax.set_ylabel("Count")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save_figure(fig, path)
    return path
