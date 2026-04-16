"""
全量特征配置：Alpha158 + Alpha360（去重）+ 基本面/筹码/价量扩展 + 成交额堆叠。

宽表字段与 ``scripts.build_qlib.to_qlib`` 一致（成交额 bin 中为 ``money``）。
成交额堆叠默认 20 日；可用 ``full_feature_config_unpruned(money_stack_days=60)`` 恢复长堆叠。

默认 ``max_features=None`` 为全量合并列；设为正整数 ``K`` 时按 LightGBM **gain** 降序取前 ``K`` 列
（需 ``feature_importance.csv`` 风格表）。路径：参数 ``importance_csv`` →
环境变量 ``QLIB_LAB_FEATURE_IMPORTANCE_CSV`` →
``scripts.qlib/handler/features/feature_importance_baseline.csv``。
常量 ``DEFAULT_HEAD_FEATURES``（100）便于显式传入 ``max_features=DEFAULT_HEAD_FEATURES``。
"""
from __future__ import annotations

from pathlib import Path

from scripts.qlib.handler.features.alpha158 import alpha158_classic_feature_config
from scripts.qlib.handler.features.alpha360 import alpha360_stacked_feature_config
from scripts.qlib.handler.features.chip import chip_feature_config
from scripts.qlib.handler.features.fundamental import fundamental_feature_config
from scripts.qlib.handler.features.importance_pick import pick_topk_fields_by_importance
from scripts.qlib.handler.features.merge import merge_feature_parts_dedup_expressions
from scripts.qlib.handler.features.money_stack import money_amount_stack_feature_config
from scripts.qlib.handler.features.raw_market import raw_market_feature_config

DEFAULT_HEAD_FEATURES = 100


def full_feature_config_unpruned(
    *,
    money_stack_days: int = 20,
    max_features: int | None = None,
    importance_csv: Path | str | None = None,
) -> tuple[list[str], list[str]]:
    """合并去重后的特征；``max_features`` 为正整数时按 gain CSV 取前 K 列；``None``/``<=0`` 为全量列。"""
    fields, names = merge_feature_parts_dedup_expressions(
        [
            alpha158_classic_feature_config(),
            alpha360_stacked_feature_config(),
            fundamental_feature_config(),
            chip_feature_config(),
            raw_market_feature_config(),
            money_amount_stack_feature_config(stack_days=money_stack_days),
        ]
    )
    if max_features is None or max_features <= 0:
        return fields, names
    return pick_topk_fields_by_importance(
        fields,
        names,
        importance_csv=importance_csv,
        top_k=max_features,
    )


def full_feature_config_pruned_top300(
    *,
    money_stack_days: int = 20,
    max_features: int | None = None,
    importance_csv: Path | str | None = None,
) -> tuple[list[str], list[str]]:
    """兼容旧导入名；曾与静态下标绑定，现与 :func:`full_feature_config_unpruned` 相同。"""
    return full_feature_config_unpruned(
        money_stack_days=money_stack_days,
        max_features=max_features,
        importance_csv=importance_csv,
    )
