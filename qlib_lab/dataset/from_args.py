"""由 CLI / ``argparse.Namespace`` 构建训练用 ``DatasetH``。"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from qlib_lab.dataset.factory import build_dataset
from qlib_lab.handler import build_training_handler, full_feature_config_pruned_top508


def build_training_dataset(
    args: argparse.Namespace,
    *,
    feature_config: tuple[list[str], list[str]] | None = None,
) -> Any:
    """在已 ``qlib.init`` 的环境下构建训练用 ``Dataset``。

    ``feature_config`` 非空时直接使用，否则为 ``full_feature_config_pruned_top508()``。
    """
    data_start, data_end = args.data_range
    fit_start, fit_end = args.train

    if feature_config is not None:
        feat_cfg = feature_config
    else:
        feat_cfg = full_feature_config_pruned_top508()
    print(f"训练特征: {len(feat_cfg[0])} 列", file=sys.stderr)

    handler = build_training_handler(
        instruments=args.instruments,
        fit_start_time=fit_start,
        fit_end_time=fit_end,
        data_start_time=data_start,
        data_end_time=data_end,
        label_expr=args.label_expr,
        feature_config=feat_cfg,
    )
    return build_dataset(
        handler,
        train=tuple(args.train),
        valid=tuple(args.valid),
        test=tuple(args.test),
    )
