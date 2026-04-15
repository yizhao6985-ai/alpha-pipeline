"""训练完成后调用 ``backtest_daily``（策略 ``signal`` 绑定为 ``(model, dataset)``）。"""
from __future__ import annotations

import copy

import pandas as pd
from qlib.contrib.evaluate import backtest_daily


def backtest_daily_with_trained(model, dataset, port_config: dict):
    """``port_config`` 含 ``strategy`` / ``backtest`` 两段，与 ``PortAnaRecord`` 配置形状一致。"""
    strat = copy.deepcopy(port_config["strategy"])
    strat["kwargs"] = {**strat["kwargs"], "signal": (model, dataset)}
    back = port_config["backtest"]
    return backtest_daily(
        start_time=back["start_time"],
        end_time=back["end_time"],
        strategy=strat,
        account=back["account"],
        benchmark=back["benchmark"],
        exchange_kwargs=back["exchange_kwargs"],
    )


def end_total_return_from_report_normal(report) -> float | None:
    """从 ``report_normal`` 的 ``account`` 列估算区间总收益：末/初 − 1。"""
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
