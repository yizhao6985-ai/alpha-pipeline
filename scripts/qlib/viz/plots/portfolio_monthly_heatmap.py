"""月度收益热力图。"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.qlib.viz.plots.common import save_figure
from scripts.qlib.viz.plots.portfolio_common import ensure_datetime_index


def plot_portfolio_monthly_heatmap(report: pd.DataFrame, path: Path) -> None:
    rep = ensure_datetime_index(report)
    r = pd.to_numeric(rep["return"], errors="coerce").fillna(0.0)
    g = r.groupby([r.index.year, r.index.month]).sum()
    years = sorted(r.index.year.unique())
    months = list(range(1, 13))
    mat = np.full((len(years), 12), np.nan)
    for i, y in enumerate(years):
        for m in months:
            try:
                mat[i, m - 1] = float(g.loc[(y, m)])
            except KeyError:
                pass
    fig, ax = plt.subplots(figsize=(14, max(4.0, len(years) * 0.45)))
    finite = mat[np.isfinite(mat)]
    if finite.size:
        absmax = max(float(np.nanmax(np.abs(finite))), 1e-9)
        im = ax.imshow(
            mat,
            aspect="auto",
            cmap="RdYlGn",
            vmin=-absmax,
            vmax=absmax,
        )
    else:
        im = ax.imshow(mat, aspect="auto", cmap="RdYlGn")
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    ax.set_xticks(range(12))
    ax.set_xticklabels([str(m) for m in months])
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels([str(y) for y in years])
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.set_title("Monthly Return Heatmap (strategy daily return, summed)")
    fig.tight_layout()
    save_figure(fig, path)
