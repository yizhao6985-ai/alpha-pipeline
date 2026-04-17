"""从 Qlib ``Recorder`` 已落盘的 workflow 产物读数并出图（编排入口）。

须在 ``with R.start(...):`` 内、且 SignalRecord / SigAnaRecord / PortAnaRecord 已 ``generate()`` 之后调用。

具体绘图在 ``scripts.qlib.viz.plots`` 各单文件模块；本模块负责 ``load_object`` 与调用顺序。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd
from qlib.utils.exceptions import LoadObjectError

from scripts.qlib.viz.plots.ic_stats import write_ic_like_stats_csv
from scripts.qlib.viz.plots.ic_cumulative import plot_ic_cumulative
from scripts.qlib.viz.plots.ic_histogram import plot_ic_histogram
from scripts.qlib.viz.plots.ic_line import plot_ic_line
from scripts.qlib.viz.plots.long_short_r_line import plot_long_short_r_line
from scripts.qlib.viz.plots.portfolio_cumulative_return import plot_portfolio_cumulative_return
from scripts.qlib.viz.plots.portfolio_drawdown import plot_portfolio_drawdown
from scripts.qlib.viz.plots.portfolio_monthly_heatmap import plot_portfolio_monthly_heatmap
from scripts.qlib.viz.plots.portfolio_risk_metrics import write_portfolio_risk_metrics_csv
from scripts.qlib.viz.plots.pred_cs_mean import plot_pred_cross_sectional_mean
from scripts.qlib.viz.plots.pred_lastday_hist import plot_pred_lastday_hist
from scripts.qlib.viz.plots.rank_ic_cumulative import plot_rank_ic_cumulative
from scripts.qlib.viz.plots.rank_ic_histogram import plot_rank_ic_histogram
from scripts.qlib.viz.plots.rank_ic_line import plot_rank_ic_line
from scripts.qlib.runtime.constants import normalize_writable_path

logger = logging.getLogger(__name__)

_PRED = "pred.pkl"
_SIG_PREFIX = "sig_analysis"
_PORT_PREFIX = "portfolio_analysis"
_REPORT_DAY = f"{_PORT_PREFIX}/report_normal_1day.pkl"


def _try_load(recorder: Any, path: str) -> Any:
    try:
        return recorder.load_object(path)
    except LoadObjectError:
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning("加载 recorder 对象失败 %s: %s", path, exc)
        return None


def account_total_return_from_recorder(recorder: Any) -> float | None:
    """从 ``portfolio_analysis/report_normal_1day.pkl`` 的 ``account`` 列估算区间总收益：末/初 − 1。"""
    report = _try_load(recorder, _REPORT_DAY)
    if report is None or not isinstance(report, pd.DataFrame) or report.empty:
        return None
    if "account" not in report.columns:
        return None
    acc = pd.to_numeric(report["account"], errors="coerce").dropna()
    if acc.empty:
        return None
    a0 = float(acc.iloc[0])
    if a0 == 0.0:
        return None
    return float(acc.iloc[-1] / a0 - 1.0)


def _append_if(path: Path | None, written: list[Path]) -> None:
    if path is not None and path.exists():
        written.append(path)


def visualize_from_recorder(
    recorder: Any,
    output_dir: Path | str,
    *,
    subdir: str = "record_viz",
) -> list[Path]:
    """从 ``Recorder`` 读取已保存对象并写入 ``output_dir/subdir/``。

    - Signal：``pred.pkl`` → ``signal/`` 下截面均值、末日分布
    - SigAna：``sig_analysis/ic.pkl``、``ric.pkl`` → 序列线、分布、累积曲线及 ``ic_stats.csv``、``rank_ic_stats.csv``；（可选）``long_short_r.pkl``
    - PortAna：``portfolio_analysis/report_normal_1day.pkl`` → ``portfolio/`` 下净值、回撤、月度热力图与 ``risk_metrics.csv``

    返回已成功写入的文件路径。
    """
    root = normalize_writable_path(output_dir) / subdir
    written: list[Path] = []

    pred = _try_load(recorder, _PRED)
    if isinstance(pred, pd.DataFrame):
        _append_if(plot_pred_cross_sectional_mean(pred, root / "signal" / "pred_cs_mean.png"), written)
        _append_if(plot_pred_lastday_hist(pred, root / "signal" / "pred_lastday_hist.png"), written)

    sig_dir = root / "sig_analysis"
    ic_raw = _try_load(recorder, f"{_SIG_PREFIX}/ic.pkl")
    _append_if(plot_ic_line(ic_raw, sig_dir / "ic.png"), written)
    _append_if(plot_ic_histogram(ic_raw, sig_dir / "ic_hist.png"), written)
    _append_if(plot_ic_cumulative(ic_raw, sig_dir / "ic_cumulative.png"), written)
    stats_ic = write_ic_like_stats_csv(ic_raw, sig_dir / "ic_stats.csv")
    _append_if(stats_ic, written)

    ric_raw = _try_load(recorder, f"{_SIG_PREFIX}/ric.pkl")
    _append_if(plot_rank_ic_line(ric_raw, sig_dir / "rank_ic.png"), written)
    _append_if(plot_rank_ic_histogram(ric_raw, sig_dir / "rank_ic_hist.png"), written)
    _append_if(plot_rank_ic_cumulative(ric_raw, sig_dir / "rank_ic_cumulative.png"), written)
    stats_ric = write_ic_like_stats_csv(ric_raw, sig_dir / "rank_ic_stats.csv")
    _append_if(stats_ric, written)

    lsr = _try_load(recorder, f"{_SIG_PREFIX}/long_short_r.pkl")
    _append_if(plot_long_short_r_line(lsr, sig_dir / "long_short_r.png"), written)

    report = _try_load(recorder, _REPORT_DAY)
    port_dir = root / "portfolio"
    if isinstance(report, pd.DataFrame) and not report.empty:
        write_portfolio_risk_metrics_csv(report, port_dir / "risk_metrics.csv")
        plot_portfolio_cumulative_return(report, port_dir / "cumulative_return.png")
        plot_portfolio_drawdown(report, port_dir / "drawdown.png")
        plot_portfolio_monthly_heatmap(report, port_dir / "monthly_return_heatmap.png")
        for name in (
            "cumulative_return.png",
            "drawdown.png",
            "monthly_return_heatmap.png",
            "risk_metrics.csv",
        ):
            cand = port_dir / name
            if cand.exists():
                written.append(cand)
    else:
        logger.info("recorder 中无 %s，跳过组合绩效图。", _REPORT_DAY)

    return written
