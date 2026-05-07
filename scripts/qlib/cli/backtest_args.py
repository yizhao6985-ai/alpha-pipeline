"""训练/回测类 CLI 共用的 ``argparse``（根目录 ``run_backtest`` / ``search_topk`` 等与 ``scripts.qlib`` 共用）。"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.qlib.handler.features.lab_fixed_features import FEATURE_PRESET_CHOICES
from scripts.qlib.handler.label import DEFAULT_LABEL_EXPR
from scripts.qlib.runtime.constants import normalize_writable_path


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
        default="csi300",
        help="标的池名称，对应 instruments/<name>.txt（默认沪深300：csi300）",
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
        default="SH000300",
        help="基准（须在 qlib_data/features 中存在，默认沪深300 SH000300）。"
        "若数据仍由旧版 399300.SZ 构建则仅有 SZ399300，可设 --benchmark SZ399300。填 None 时改用 SH000300",
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
        "--label-preset",
        type=str,
        default=None,
        choices=["t1", "t5", "t20"],
        help="标签预设：t1 同默认；t5/t20 为多日持有期收益，与一日调仓回测不完全一致，仅作 IC 试验。若设置则覆盖 --label-expr",
    )
    p.add_argument(
        "--feature-norm",
        type=str,
        default="robust_zscore",
        choices=["robust_zscore", "cs_rank"],
        help="推理侧特征归一：robust_zscore（默认，test 通常更稳）；冲 Rank IC 时可试 cs_rank",
    )
    p.add_argument(
        "--feature-preset",
        type=str,
        default="full",
        choices=list(FEATURE_PRESET_CHOICES),
        metavar="PRESET",
        help="特征消融：full=55 维（默认）；no_overnight 去 3 个隔夜 MKT；"
        "no_fund 去 FUND_RAW_*；no_mkt 去 MKT_RAW_*；"
        "lean 兼容旧 CLI（等同 no_overnight）",
    )
    g_lgb = p.add_argument_group(
        "LightGBM（默认见 scripts/qlib/model/constants.py；未传则沿用默认）"
    )
    g_lgb.add_argument("--lgb-learning-rate", type=float, default=None)
    g_lgb.add_argument("--lgb-max-depth", type=int, default=None)
    g_lgb.add_argument("--lgb-num-leaves", type=int, default=None)
    g_lgb.add_argument("--lgb-min-data-in-leaf", type=int, default=None)
    g_lgb.add_argument("--lgb-lambda-l1", type=float, default=None)
    g_lgb.add_argument("--lgb-lambda-l2", type=float, default=None)
    g_lgb.add_argument("--lgb-feature-fraction", type=float, default=None)
    g_lgb.add_argument("--lgb-bagging-fraction", type=float, default=None)
    g_lgb.add_argument("--lgb-num-boost-round", type=int, default=None)
    g_lgb.add_argument("--lgb-early-stopping-rounds", type=int, default=None)
    p.add_argument(
        "--topk", type=int, default=4, help="收盘调仓 TopK：每日尾盘持仓只数"
    )
    p.add_argument(
        "--n-drop",
        type=int,
        default=1,
        help="策略头部剔除：预测分降序先丢弃前 n 名再取 TopK（默认 1；0 表示不剔除）",
    )
    p.add_argument(
        "--risk-degree",
        type=float,
        default=0.99,
        help="仓位占资金比例上限（Topk 策略 risk_degree）",
    )
    p.add_argument(
        "--dump-train-csv",
        action="store_true",
        help="训练开始前导出 train 段特征/标签矩阵到 <output-dir>/train_matrix_preview/（CSV，数据量大时慎用）",
    )
    return p


def finalize_backtest_cli_args(ns: argparse.Namespace) -> argparse.Namespace:
    """统一修正 ``--output-dir`` 等路径（须在 parse 之后调用）。"""
    ns.output_dir = normalize_writable_path(ns.output_dir)
    preset = getattr(ns, "label_preset", None)
    if preset is not None:
        from scripts.qlib.handler.label_presets import LABEL_PRESETS

        ns.label_expr = LABEL_PRESETS[preset]
    return ns


def parse_args() -> argparse.Namespace:
    return finalize_backtest_cli_args(build_arg_parser().parse_args())
