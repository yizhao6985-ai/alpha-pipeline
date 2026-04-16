"""回测 ``report_normal``：``risk_analysis`` 指标 CSV + 净值 / 回撤 / 月度收益热力图。"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from qlib.contrib.evaluate import risk_analysis


def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index, errors="coerce")
    return out.sort_index()


def build_risk_metrics_dataframe(report_normal: pd.DataFrame) -> pd.DataFrame:
    """与 Qlib ``risk_analysis`` 一致：无成本 / 含成本超额日收益的绩效指标。"""
    need = {"return", "bench", "cost"}
    if not need <= set(report_normal.columns):
        missing = need - set(report_normal.columns)
        raise ValueError(f"report_normal 缺少列: {sorted(missing)}")
    r = pd.to_numeric(report_normal["return"], errors="coerce").fillna(0.0)
    b = pd.to_numeric(report_normal["bench"], errors="coerce").fillna(0.0)
    c = pd.to_numeric(report_normal["cost"], errors="coerce").fillna(0.0)
    ex_wo = r - b
    ex_w = ex_wo - c
    wo = risk_analysis(ex_wo, freq="day")
    w = risk_analysis(ex_w, freq="day")
    merged = pd.concat([wo, w], axis=1)
    merged.columns = ["excess_return_without_cost", "excess_return_with_cost"]
    merged.index.name = "metric"
    return merged


def _plot_cumulative_return(report: pd.DataFrame, path: Path) -> None:
    rep = _ensure_datetime_index(report)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_drawdown(report: pd.DataFrame, path: Path) -> None:
    rep = _ensure_datetime_index(report)
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
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_monthly_heatmap(report: pd.DataFrame, path: Path) -> None:
    rep = _ensure_datetime_index(report)
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
    im = ax.imshow(mat, aspect="auto", cmap="YlGnBu")
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    ax.set_xticks(range(12))
    ax.set_xticklabels([str(m) for m in months])
    ax.set_yticks(range(len(years)))
    ax.set_yticklabels([str(y) for y in years])
    ax.set_xlabel("Month")
    ax.set_ylabel("Year")
    ax.set_title("Monthly Return Heatmap (strategy daily return, summed)")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def save_backtest_analysis(
    report_normal: pd.DataFrame | None,
    out_dir: Path,
) -> None:
    """写入 ``risk_metrics.csv``、``cumulative_return.png``、``drawdown.png``、``monthly_return_heatmap.png``。"""
    if report_normal is None or not isinstance(report_normal, pd.DataFrame) or report_normal.empty:
        return
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = build_risk_metrics_dataframe(report_normal)
    metrics.reset_index().to_csv(out_dir / "risk_metrics.csv", index=False)
    _plot_cumulative_return(report_normal, out_dir / "cumulative_return.png")
    _plot_drawdown(report_normal, out_dir / "drawdown.png")
    _plot_monthly_heatmap(report_normal, out_dir / "monthly_return_heatmap.png")
