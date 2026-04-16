"""由 CLI / ``argparse.Namespace`` 构建训练用 ``DatasetH``。"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from scripts.qlib.dataset.factory import build_dataset
from scripts.qlib.handler import build_training_handler, full_feature_config_unpruned


def build_training_dataset(
    args: argparse.Namespace,
    *,
    feature_config: tuple[list[str], list[str]] | None = None,
) -> Any:
    """在已 ``qlib.init`` 的环境下构建训练用 ``Dataset``。

    ``feature_config`` 非空时直接使用，否则为 ``full_feature_config_unpruned()``：
    默认 ``--feature-top-k 0`` 为全量列；``K>0`` 时按 ``--feature-importance-csv``（或环境变量 /
    baseline 路径）的 gain 截取前 K 列。
    """
    data_start, data_end = args.data_range
    fit_start, fit_end = args.train

    if feature_config is not None:
        feat_cfg = feature_config
    else:
        top_k = int(getattr(args, "feature_top_k", 0))
        fi_csv = getattr(args, "feature_importance_csv", None)
        feat_cfg = full_feature_config_unpruned(
            max_features=None if top_k <= 0 else top_k,
            importance_csv=fi_csv,
        )
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
