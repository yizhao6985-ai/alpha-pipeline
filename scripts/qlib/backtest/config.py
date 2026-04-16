"""Qlib ``port_config``：strategy 与 backtest 在同处一次性构造。"""
from __future__ import annotations

import argparse

from scripts.qlib.backtest.constants import EXCHANGE_DEAL_PRICE
from scripts.qlib.strategy.constants import (
    OVERNIGHT_TOPK_STRATEGY_CLASS,
    OVERNIGHT_TOPK_STRATEGY_MODULE,
)


def build_port_config_from_args(args: argparse.Namespace) -> dict:
    """``backtest_daily`` / ``PortAnaRecord`` 用 ``port_config``（收盘 TopK + 交易所段）。"""
    if args.benchmark.lower() in {"none", ""}:
        benchmark = "SH000510"
        print("提示: benchmark 为空时已改用 SH000510（中证A500）作基准。")
    else:
        benchmark = args.benchmark

    return {
        "strategy": {
            "class": OVERNIGHT_TOPK_STRATEGY_CLASS,
            "module_path": OVERNIGHT_TOPK_STRATEGY_MODULE,
            "kwargs": {
                "signal": "<PRED>",
                "topk": args.topk,
                "risk_degree": args.risk_degree,
                "only_tradable": True,
                "forbid_all_trade_at_limit": False,
            },
        },
        "backtest": {
            "start_time": args.test[0],
            "end_time": args.test[1],
            "account": args.account,
            "benchmark": benchmark,
            "exchange_kwargs": {
                "limit_threshold": 0.095,
                "deal_price": EXCHANGE_DEAL_PRICE,
                "open_cost": 0.0005,
                "close_cost": 0.0015,
                "min_cost": 5,
            },
        },
    }
