"""在 Qlib Workflow 内训练 LightGBM。"""
from __future__ import annotations

import argparse

from qlib.contrib.model.gbdt import LGBModel

from scripts.qlib.model.constants import (
    LGB_EARLY_STOPPING_ROUNDS,
    LGB_KWARGS,
    LGB_NUM_BOOST_ROUND,
)


def _lgb_params_from_args(args: argparse.Namespace) -> dict:
    """CLI 覆盖 :data:`LGB_KWARGS`；未出现的键沿用默认。"""
    kw = dict(LGB_KWARGS)
    overrides: list[tuple[str, str]] = [
        ("lgb_learning_rate", "learning_rate"),
        ("lgb_max_depth", "max_depth"),
        ("lgb_num_leaves", "num_leaves"),
        ("lgb_min_data_in_leaf", "min_data_in_leaf"),
        ("lgb_lambda_l1", "lambda_l1"),
        ("lgb_lambda_l2", "lambda_l2"),
        ("lgb_feature_fraction", "feature_fraction"),
        ("lgb_bagging_fraction", "bagging_fraction"),
    ]
    for attr, key in overrides:
        v = getattr(args, attr, None)
        if v is not None:
            kw[key] = v
    return kw


def fit_model_generate_pred(
    args: argparse.Namespace,
    dataset,
) -> LGBModel:
    """训练模型（须在 ``with R.start():`` 内调用以写入训练指标）。"""
    params = _lgb_params_from_args(args)
    num_boost = getattr(args, "lgb_num_boost_round", None)
    early = getattr(args, "lgb_early_stopping_rounds", None)
    model = LGBModel(
        num_boost_round=num_boost if num_boost is not None else LGB_NUM_BOOST_ROUND,
        early_stopping_rounds=early if early is not None else LGB_EARLY_STOPPING_ROUNDS,
        **params,
    )
    model.fit(dataset)
    return model
