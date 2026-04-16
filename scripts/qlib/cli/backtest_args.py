"""训练/回测类 CLI 共用的 ``argparse``（根目录 ``run_backtest`` / ``search_topk`` 等与 ``scripts.qlib`` 共用）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.qlib.handler.label import DEFAULT_LABEL_EXPR


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Qlib：LightGBM + 收盘调仓 TopK 回测")
    p.add_argument(
        "--provider-uri",
        type=str,
        default=None,
        help="Qlib 数据目录（默认同级 qlib_data）",
    )
    p.add_argument(
        "--instruments",
        type=str,
        default="csi_a500",
        help="标的池名称，对应 instruments/<name>.txt（默认中证A500：csi_a500）",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("qlib_runs") / "plots",
        help="输出目录：默认写入 feature_importance.csv",
    )
    p.add_argument("--experiment-name", type=str, default="qlpha-pipeline_topk")
    p.add_argument("--account", type=float, default=100_000.0, help="回测初始资金")
    p.add_argument(
        "--benchmark",
        type=str,
        default="SH000510",
        help="基准（须在 qlib_data/features 中存在，默认中证A500 SH000510）。填 None 时改用 SH000510",
    )
    p.add_argument(
        "--train",
        type=str,
        nargs=2,
        default=("2018-01-02", "2022-12-31"),
        metavar=("START", "END"),
    )
    p.add_argument(
        "--valid",
        type=str,
        nargs=2,
        default=("2023-01-01", "2023-12-31"),
        metavar=("START", "END"),
    )
    p.add_argument(
        "--test",
        type=str,
        nargs=2,
        default=("2024-01-01", "2026-04-10"),
        metavar=("START", "END"),
    )
    p.add_argument(
        "--data-range",
        type=str,
        nargs=2,
        default=("2018-01-02", "2026-04-10"),
        metavar=("START", "END"),
        help="Handler 拉取原始数据的区间（应覆盖 train/valid/test）",
    )
    p.add_argument(
        "--label-expr",
        type=str,
        default=DEFAULT_LABEL_EXPR,
        help="训练用标签（默认 T+1 收盘相对 T 日收盘，须配合收盘撮合价）",
    )
    p.add_argument(
        "--topk", type=int, default=4, help="收盘调仓 TopK：每日尾盘持仓只数"
    )
    p.add_argument(
        "--risk-degree",
        type=float,
        default=0.95,
        help="仓位占资金比例上限（Topk 策略 risk_degree）",
    )
    return p


def parse_args() -> argparse.Namespace:
    return build_arg_parser().parse_args()
