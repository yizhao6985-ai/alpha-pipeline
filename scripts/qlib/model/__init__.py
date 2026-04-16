"""模型封装：Qlib LightGBM 与训练入口。"""
from __future__ import annotations

from qlib.contrib.model.gbdt import LGBModel

from scripts.qlib.model.constants import (
    LGB_EARLY_STOPPING_ROUNDS,
    LGB_KWARGS,
    LGB_NUM_BOOST_ROUND,
)
from scripts.qlib.model.fit import fit_model_generate_pred

__all__ = [
    "LGBModel",
    "LGB_EARLY_STOPPING_ROUNDS",
    "LGB_KWARGS",
    "LGB_NUM_BOOST_ROUND",
    "fit_model_generate_pred",
]
