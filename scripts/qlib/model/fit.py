"""在 Qlib Workflow 内训练 LightGBM。"""
from __future__ import annotations

import argparse

from qlib.contrib.model.gbdt import LGBModel

from scripts.qlib.model.constants import (
    LGB_EARLY_STOPPING_ROUNDS,
    LGB_KWARGS,
    LGB_NUM_BOOST_ROUND,
)


def fit_model_generate_pred(
    args: argparse.Namespace,
    dataset,
) -> LGBModel:
    """训练模型（须在 ``with R.start():`` 内调用以写入训练指标）。"""
    _ = args

    model = LGBModel(
        num_boost_round=LGB_NUM_BOOST_ROUND,
        early_stopping_rounds=LGB_EARLY_STOPPING_ROUNDS,
        **LGB_KWARGS,
    )
    model.fit(dataset)
    return model
