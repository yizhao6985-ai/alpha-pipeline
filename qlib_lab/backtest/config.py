"""``port_config[\"backtest\"]``：区间、资金、基准、交易所参数。"""
from __future__ import annotations

import argparse

from qlib_lab.backtest.constants import EXCHANGE_DEAL_PRICE


def build_backtest_config_from_args(args: argparse.Namespace) -> dict:
    if args.benchmark.lower() in {"none", ""}:
        benchmark = "SH000510"
        print("提示: benchmark 为空时已改用 SH000510（中证A500）作基准。")
    else:
        benchmark = args.benchmark

    return {
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
    }
