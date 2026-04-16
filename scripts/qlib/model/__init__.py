"""模型封装：Qlib LightGBM 与训练入口。"""
from __future__ import annotations

from qlib.contrib.model.gbdt import LGBModel

from scripts.qlib.model.constants import (
    LGB_EARLY_STOPPING_ROUNDS,
    LGB_KWARGS,
    LGB_NUM_BOOST_ROUND,
)
from scripts.qlib.model.fit import fit_model_generate_pred
from scripts.qlib.model.importance import feature_importance_for_export, order_indices_by_gain

__all__ = [
    "LGBModel",
    "LGB_EARLY_STOPPING_ROUNDS",
    "LGB_KWARGS",
    "LGB_NUM_BOOST_ROUND",
    "feature_importance_for_export",
    "fit_model_generate_pred",
    "order_indices_by_gain",
]
