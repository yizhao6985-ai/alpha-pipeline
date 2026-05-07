"""由 CLI / ``argparse.Namespace`` 构建训练用 ``DatasetH``。"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from scripts.qlib.dataset.factory import build_dataset
from scripts.qlib.handler import (
    build_training_handler,
    lab_fixed_feature_config,
    lab_fixed_feature_config_for_preset,
)


def _feature_config_from_args(args: argparse.Namespace) -> tuple[list[str], list[str]]:
    """默认与 CLI 一致（``full``=55 维全量特征，不含筹码）。"""
    preset = getattr(args, "feature_preset", "full")
    if preset == "full":
        return lab_fixed_feature_config()
    return lab_fixed_feature_config_for_preset(preset)


def build_training_dataset(args: argparse.Namespace) -> Any:
    """在已 ``qlib.init`` 的环境下构建训练用 ``Dataset``。

    特征为 ``handler.features.lab_fixed_features`` 中定义的固定列，不接受外部 ``feature_config``。
    """
    data_start, data_end = args.data_range
    fit_start, fit_end = args.train

    feat_cfg = _feature_config_from_args(args)
    preset = getattr(args, "feature_preset", "full")
    print(
        f"训练特征: {len(feat_cfg[0])} 列 (preset={preset})",
        file=sys.stderr,
    )

    handler = build_training_handler(
        instruments=args.instruments,
        fit_start_time=fit_start,
        fit_end_time=fit_end,
        data_start_time=data_start,
        data_end_time=data_end,
        label_expr=args.label_expr,
        feature_config=feat_cfg,
        feature_norm=getattr(args, "feature_norm", "robust_zscore"),
    )
    return build_dataset(
        handler,
        train=tuple(args.train),
        valid=tuple(args.valid),
        test=tuple(args.test),
    )


def _build_training_dataset_with_fields(
    args: argparse.Namespace,
    fields: list[str],
    names: list[str],
) -> Any:
    """与 ``build_training_dataset`` 相同数据分段与 handler 设置，仅特征子集不同（仅 ``sweep_tail_features`` 使用）。"""
    data_start, data_end = args.data_range
    fit_start, fit_end = args.train
    handler = build_training_handler(
        instruments=args.instruments,
        fit_start_time=fit_start,
        fit_end_time=fit_end,
        data_start_time=data_start,
        data_end_time=data_end,
        label_expr=args.label_expr,
        feature_config=(fields, names),
        feature_norm=getattr(args, "feature_norm", "robust_zscore"),
    )
    return build_dataset(
        handler,
        train=tuple(args.train),
        valid=tuple(args.valid),
        test=tuple(args.test),
    )
