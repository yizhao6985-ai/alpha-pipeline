"""训练/回测相关 CLI 的共用 ``argparse``（``backtest_args``）。"""
from __future__ import annotations

from scripts.qlib.cli.backtest_args import build_arg_parser, parse_args

__all__ = ["build_arg_parser", "parse_args"]
