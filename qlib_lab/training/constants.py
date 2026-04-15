"""LightGBM 训练默认超参。"""
from __future__ import annotations

LGB_NUM_BOOST_ROUND: int = 300
LGB_EARLY_STOPPING_ROUNDS: int = 50
LGB_KWARGS: dict = dict(
    max_depth=8,
    num_leaves=64,
    learning_rate=0.05,
    colsample_bytree=0.85,
    subsample=0.85,
    lambda_l1=0.0,
    lambda_l2=1.0,
    min_data_in_leaf=20,
)
