"""
特征字段配置（按块拆分）：Alpha158/360、基本面、筹码、价量扩展、成交额堆叠及全量合并。
"""
from __future__ import annotations

from qlib_lab.handler.features.alpha158 import alpha158_classic_feature_config
from qlib_lab.handler.features.alpha360 import alpha360_stacked_feature_config
from qlib_lab.handler.features.chip import chip_feature_config
from qlib_lab.handler.features.full import full_feature_config_pruned_top508, full_feature_config_unpruned
from qlib_lab.handler.features.fundamental import fundamental_feature_config
from qlib_lab.handler.features.merge import merge_feature_parts_dedup_expressions
from qlib_lab.handler.features.money_stack import money_amount_stack_feature_config
from qlib_lab.handler.features.raw_market import raw_market_feature_config

__all__ = [
    "alpha158_classic_feature_config",
    "alpha360_stacked_feature_config",
    "chip_feature_config",
    "full_feature_config_pruned_top508",
    "full_feature_config_unpruned",
    "fundamental_feature_config",
    "merge_feature_parts_dedup_expressions",
    "money_amount_stack_feature_config",
    "raw_market_feature_config",
]
