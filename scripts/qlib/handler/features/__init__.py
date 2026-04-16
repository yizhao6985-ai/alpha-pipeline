"""
特征字段配置（按块拆分）：Alpha158/360、基本面、筹码、价量扩展、成交额堆叠；默认全量合并，``DEFAULT_HEAD_FEATURES`` 为常用截取数量常量。
"""
from __future__ import annotations

from scripts.qlib.handler.features.alpha158 import alpha158_classic_feature_config
from scripts.qlib.handler.features.alpha360 import alpha360_stacked_feature_config
from scripts.qlib.handler.features.chip import chip_feature_config
from scripts.qlib.handler.features.full import (
    DEFAULT_HEAD_FEATURES,
    full_feature_config_pruned_top300,
    full_feature_config_unpruned,
)
from scripts.qlib.handler.features.importance_pick import (
    load_importance_gain_csv,
    order_indices_by_gain,
    pick_topk_fields_by_importance,
    resolve_importance_csv_path,
)
from scripts.qlib.handler.features.fundamental import fundamental_feature_config
from scripts.qlib.handler.features.merge import merge_feature_parts_dedup_expressions
from scripts.qlib.handler.features.money_stack import money_amount_stack_feature_config
from scripts.qlib.handler.features.raw_market import raw_market_feature_config

__all__ = [
    "DEFAULT_HEAD_FEATURES",
    "load_importance_gain_csv",
    "order_indices_by_gain",
    "pick_topk_fields_by_importance",
    "resolve_importance_csv_path",
    "alpha158_classic_feature_config",
    "alpha360_stacked_feature_config",
    "chip_feature_config",
    "full_feature_config_pruned_top300",
    "full_feature_config_unpruned",
    "fundamental_feature_config",
    "merge_feature_parts_dedup_expressions",
    "money_amount_stack_feature_config",
    "raw_market_feature_config",
]
