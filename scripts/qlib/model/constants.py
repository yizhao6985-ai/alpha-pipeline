"""LightGBM 训练默认超参（经 Qlib ``LGBModel`` 原样传入 ``lgb.train`` 的 ``params``）。

原先用 ``subsample`` / ``colsample_bytree`` 且未设 ``bagging_freq`` 时，LightGBM 默认
``bagging_freq=0``，行 bagging 基本不生效，``subsample`` 形同虚设。这里改为
``bagging_fraction`` + ``bagging_freq=1``，与官方推荐一致。

日频截面：样本多、标签噪声大，用中等树深、略大的 ``min_data_in_leaf`` 抑制碎叶子过拟合；
``num_boost_round`` 仅作上限，实际长度由验证集 early stopping 决定。具体数值是通用起点，仍应在 valid 上再调。
"""
from __future__ import annotations

from typing import Any

# 与 Qlib ``LGBModel`` 构造默认一致；真正停在哪一轮由 early_stopping 决定
LGB_NUM_BOOST_ROUND: int = 1000
LGB_EARLY_STOPPING_ROUNDS: int = 80

LGB_KWARGS: dict[str, Any] = dict(
    learning_rate=0.042,
    max_depth=8,
    num_leaves=127,
    feature_fraction=0.85,
    bagging_fraction=0.85,
    bagging_freq=1,
    lambda_l1=0.1,
    lambda_l2=1.0,
    min_data_in_leaf=100,
)
