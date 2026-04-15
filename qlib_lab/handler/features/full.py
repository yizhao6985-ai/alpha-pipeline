"""
全量特征配置：Alpha158 + Alpha360（去重）+ 基本面/筹码/价量扩展 + 成交额堆叠。

宽表字段与 ``scripts/process_to_qlib.py`` 一致（成交额 bin 中为 ``money``）。
"""
from __future__ import annotations

from qlib_lab.handler.features.alpha158 import alpha158_classic_feature_config
from qlib_lab.handler.features.alpha360 import alpha360_stacked_feature_config
from qlib_lab.handler.features.chip import chip_feature_config
from qlib_lab.handler.features.fundamental import fundamental_feature_config
from qlib_lab.handler.features.merge import merge_feature_parts_dedup_expressions
from qlib_lab.handler.features.money_stack import money_amount_stack_feature_config
from qlib_lab.handler.features.raw_market import raw_market_feature_config
from qlib_lab.handler.features.full_pruned_top508_indices import FULL_PRUNED_TOP508_INDICES


def full_feature_config_unpruned() -> tuple[list[str], list[str]]:
    """全量特征（不读 importance CSV）。"""
    return merge_feature_parts_dedup_expressions(
        [
            alpha158_classic_feature_config(),
            alpha360_stacked_feature_config(),
            fundamental_feature_config(),
            chip_feature_config(),
            raw_market_feature_config(),
            money_amount_stack_feature_config(),
        ]
    )


def full_feature_config_pruned_top508() -> tuple[list[str], list[str]]:
    """按 ``feature_importance.csv`` 中 gain 排序保留前 508 列（与训练时 ``Column_k`` 下标对齐）。"""
    fields, names = full_feature_config_unpruned()
    idx = FULL_PRUNED_TOP508_INDICES
    if len(idx) != 508 or len(set(idx)) != 508:
        raise RuntimeError("FULL_PRUNED_TOP508_INDICES 须为 508 个互异下标")
    n = len(fields)
    if n != len(names):
        raise RuntimeError("feature fields/names 长度不一致")
    bad = [i for i in idx if i < 0 or i >= n]
    if bad:
        raise RuntimeError(f"裁剪下标越界（全量列数 {n}）: {bad[:5]}...")
    return [fields[i] for i in idx], [names[i] for i in idx]
