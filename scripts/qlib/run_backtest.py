#!/usr/bin/env python3
"""
单轮：全量特征 + LightGBM + 日频回测与落盘。编排逻辑见 ``scripts.qlib.backtest.pipeline``。

执行::

    python -m scripts.qlib run_backtest
    python -m scripts.qlib.run_backtest
    python scripts/run_backtest.py
"""
from __future__ import annotations

from scripts.qlib.backtest.pipeline import run_backtest_pipeline
from scripts.qlib.cli.backtest_args import parse_args
from scripts.qlib.runtime import init_qlib_for_backtest


def main() -> int:
    args = parse_args()
    init_qlib_for_backtest(args)
    run_backtest_pipeline(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
