"""组合回测：``port_config``、撮合默认值、``backtest_daily`` 封装。"""
from __future__ import annotations

from scripts.qlib.backtest.config import build_port_config_from_args
from scripts.qlib.backtest.constants import EXCHANGE_DEAL_PRICE
from scripts.qlib.backtest.daily_runner import (
    backtest_daily_with_trained,
    end_total_return_from_report_normal,
)
from scripts.qlib.backtest.plotting import save_backtest_analysis
from scripts.qlib.backtest.raw_export import save_backtest_raw_outputs
from scripts.qlib.backtest.pipeline import run_backtest_pipeline, run_backtest_save_artifacts

__all__ = [
    "EXCHANGE_DEAL_PRICE",
    "backtest_daily_with_trained",
    "build_port_config_from_args",
    "end_total_return_from_report_normal",
    "run_backtest_pipeline",
    "run_backtest_save_artifacts",
    "save_backtest_analysis",
    "save_backtest_raw_outputs",
]
