"""``backtest_daily`` 输出的 ``report_normal`` / ``positions_normal`` 绘图。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_report_normal(report: pd.DataFrame | None, out_png: Path) -> None:
    """折线图：``account``、``bench``（若有）、``return``（若有）。"""
    if report is None or not isinstance(report, pd.DataFrame) or report.empty:
        return
    out_png.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    idx = report.index

    if "account" in report.columns:
        s = pd.to_numeric(report["account"], errors="coerce")
        ax.plot(idx, s.values, label="account (portfolio)", linewidth=1.2)
    if "bench" in report.columns:
        s = pd.to_numeric(report["bench"], errors="coerce")
        ax.plot(idx, s.values, label="bench", alpha=0.75, linewidth=1.0)
    if "return" in report.columns and "account" not in report.columns:
        s = pd.to_numeric(report["return"], errors="coerce")
        ax.plot(idx, s.values.cumsum(), label="cum return (sum)", linewidth=1.0)

    ax.set_title("Backtest report_normal")
    ax.set_xlabel("date")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_positions_dataframe(df: pd.DataFrame, out_png: Path, title_suffix: str = "") -> None:
    if df.empty:
        return
    out_png.parent.mkdir(parents=True, exist_ok=True)

    # MultiIndex (datetime, instrument) -> 单列权重
    if isinstance(df.index, pd.MultiIndex) and df.index.nlevels >= 2:
        try:
            col = df.columns[0] if len(df.columns) else None
            ser = df.iloc[:, 0] if col is not None else df.squeeze()
            if not isinstance(ser, pd.Series):
                return
            wide = ser.unstack(fill_value=0.0)
            if not isinstance(wide, pd.DataFrame) or wide.empty:
                return
            _heatmap_weights(wide, out_png, title_suffix)
        except (ValueError, KeyError):
            pass
        return

    # 行=日期，列=标的
    num = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if num.shape[1] == 0:
        return
    if num.shape[1] > 120:
        _plot_position_stats(num, out_png, title_suffix)
    else:
        _heatmap_weights(num, out_png, title_suffix)


def _heatmap_weights(wide: pd.DataFrame, out_png: Path, title_suffix: str) -> None:
    """``wide``：索引为日期，列为标的，值为权重。"""
    arr = wide.to_numpy(dtype=float)
    if arr.size == 0:
        return
    fig, ax = plt.subplots(figsize=(12, max(4.0, min(18.0, wide.shape[1] * 0.12))))
    vmax = float(np.nanmax(arr)) if np.isfinite(arr).any() else 0.0
    vmax = max(vmax, 1e-8)
    im = ax.imshow(
        arr.T,
        aspect="auto",
        interpolation="nearest",
        cmap="YlOrRd",
        vmin=0.0,
        vmax=vmax,
    )
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.02, label="weight")
    n = len(wide.index)
    tick_step = max(1, n // 12)
    ax.set_xticks(range(0, n, tick_step))
    ax.set_xticklabels([str(wide.index[i])[:10] for i in range(0, n, tick_step)], rotation=45, ha="right")
    ax.set_yticks(range(0, wide.shape[1], max(1, wide.shape[1] // 15)))
    ax.set_yticklabels(
        [str(wide.columns[i]) for i in range(0, wide.shape[1], max(1, wide.shape[1] // 15))],
        fontsize=7,
    )
    ax.set_title(f"Position weights heatmap{title_suffix}")
    ax.set_xlabel("trading day index")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _plot_position_stats(num: pd.DataFrame, out_png: Path, title_suffix: str) -> None:
    """标的过多时：持仓数、最大权重、总绝对权重。"""
    fig, axes = plt.subplots(3, 1, figsize=(11, 7), sharex=True)
    thr = 1e-6
    n_hold = (num.abs() > thr).sum(axis=1)
    max_w = num.abs().max(axis=1)
    sum_abs = num.abs().sum(axis=1)

    axes[0].plot(num.index, n_hold.values, color="C0", linewidth=1.0)
    axes[0].set_ylabel("# positions")
    axes[0].set_title(f"Position stats{title_suffix}")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(num.index, max_w.values, color="C1", linewidth=1.0)
    axes[1].set_ylabel("max |w|")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(num.index, sum_abs.values, color="C2", linewidth=1.0)
    axes[2].set_ylabel("sum |w|")
    axes[2].set_xlabel("date")
    axes[2].grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_positions_normal(positions: Any, out_dir: Path, stem: str = "positions_normal") -> None:
    """支持 ``dict[str, DataFrame]`` 或单个 ``DataFrame``。"""
    if positions is None:
        return
    if isinstance(positions, pd.DataFrame):
        _plot_positions_dataframe(positions, out_dir / f"{stem}.png", "")
        return
    if isinstance(positions, dict):
        if not positions:
            return
        for key, val in positions.items():
            if not isinstance(val, pd.DataFrame):
                continue
            safe = str(key).replace("/", "_").replace("\\", "_")
            suf = f" ({safe})" if len(positions) > 1 else ""
            _plot_positions_dataframe(val, out_dir / f"{stem}_{safe}.png", suf)
        return


def save_backtest_plots(
    report_normal: pd.DataFrame | None,
    positions_normal: Any,
    out_dir: Path,
) -> None:
    """写入 ``report_normal.png`` 与 ``positions_normal*.png``。"""
    plot_report_normal(report_normal, out_dir / "report_normal.png")
    plot_positions_normal(positions_normal, out_dir, stem="positions_normal")
