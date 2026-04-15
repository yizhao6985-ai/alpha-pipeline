"""``port_config[\"strategy\"]``：由 CLI 等构造。"""
from __future__ import annotations

import argparse

from qlib_lab.strategy.constants import (
    OVERNIGHT_TOPK_STRATEGY_CLASS,
    OVERNIGHT_TOPK_STRATEGY_MODULE,
)


def build_strategy_config_from_args(args: argparse.Namespace) -> dict:
    """收盘调仓 TopK；工作流中 ``signal`` 为 ``\"<PRED>\"``，``backtest_daily`` 可改为 ``(model, dataset)``。"""
    return {
        "class": OVERNIGHT_TOPK_STRATEGY_CLASS,
        "module_path": OVERNIGHT_TOPK_STRATEGY_MODULE,
        "kwargs": {
            "signal": "<PRED>",
            "topk": args.topk,
            "risk_degree": args.risk_degree,
            "only_tradable": True,
            "forbid_all_trade_at_limit": False,
        },
    }
