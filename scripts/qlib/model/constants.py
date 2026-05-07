"""LightGBM 训练默认超参（经 Qlib ``LGBModel`` 原样传入 ``lgb.train`` 的 ``params``）。

原先用 ``subsample`` / ``colsample_bytree`` 且未设 ``bagging_freq`` 时，LightGBM 默认
``bagging_freq=0``，行 bagging 基本不生效，``subsample`` 形同虚设。这里改为
``bagging_fraction`` + ``bagging_freq=1``，与官方推荐一致。

**日频截面 + 噪声标签**（IC/截面 z-score 等）：在特征维数约几十、样本量大的设定下，
略小的 ``num_leaves`` / ``max_depth`` 通常比「深树 + 多叶」更稳，减轻 train 相对 valid/test 的虚高；
``min_data_in_leaf`` 略抬可抑制碎叶子；``lambda_l1``/``lambda_l2`` 略增可压过拟合。
``learning_rate`` 取 0.05 与常见实践一致，真正停在哪一轮仍由 ``early_stopping_rounds`` 决定。

若训练窗很短、单日截面股票数很少，可酌情下调 ``min_data_in_leaf``（例如 120）或略增 ``num_leaves``。

默认超参与 ``--feature-norm robust_zscore`` 搭配，在样本外 test 上通常比 ``cs_rank`` + 大叶数更稳；
若仍要冲 Rank IC，可试 ``--feature-norm cs_rank`` 并酌情调 ``--lgb-*``。
"""
from __future__ import annotations

from typing import Any

# 与 Qlib ``LGBModel`` 构造默认一致；真正停在哪一轮由 early stopping 决定
LGB_NUM_BOOST_ROUND: int = 1000
LGB_EARLY_STOPPING_ROUNDS: int = 115

# 折中：兼顾 test 样本外 IC/Rank IC（避免 cs_rank+大叶 导致的 test 下滑）
LGB_KWARGS: dict[str, Any] = dict(
    learning_rate=0.05,
    max_depth=6,
    num_leaves=56,
    feature_fraction=0.78,
    bagging_fraction=0.85,
    bagging_freq=1,
    lambda_l1=0.14,
    lambda_l2=1.12,
    min_data_in_leaf=165,
)
