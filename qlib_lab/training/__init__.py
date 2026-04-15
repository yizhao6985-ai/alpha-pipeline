"""模型训练（与具体回测实现解耦）。"""
from __future__ import annotations

from qlib_lab.training.constants import (
    LGB_EARLY_STOPPING_ROUNDS,
    LGB_KWARGS,
    LGB_NUM_BOOST_ROUND,
)
from qlib_lab.training.fit import fit_model_generate_pred

__all__ = [
    "LGB_EARLY_STOPPING_ROUNDS",
    "LGB_KWARGS",
    "LGB_NUM_BOOST_ROUND",
    "fit_model_generate_pred",
]
