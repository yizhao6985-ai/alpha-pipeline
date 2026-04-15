"""组合回测：``port_config`` 回测段、撮合默认值、``backtest_daily`` 封装。"""
from __future__ import annotations

from qlib_lab.backtest.config import build_backtest_config_from_args
from qlib_lab.backtest.constants import EXCHANGE_DEAL_PRICE
from qlib_lab.backtest.daily_runner import (
    backtest_daily_with_trained,
    end_total_return_from_report_normal,
)
from qlib_lab.backtest.plotting import save_backtest_plots

__all__ = [
    "EXCHANGE_DEAL_PRICE",
    "backtest_daily_with_trained",
    "build_backtest_config_from_args",
    "end_total_return_from_report_normal",
    "save_backtest_plots",
]
