"""成交额 60 日归一化堆叠特征。"""
from __future__ import annotations


def money_amount_stack_feature_config() -> tuple[list[str], list[str]]:
    """成交额60 日归一化堆叠（与 Alpha360 对 ``$volume`` 形式一致，Alpha158/360 均不含 ``$money`` 原始堆叠）。"""
    fields: list[str] = []
    names: list[str] = []
    for i in range(59, 0, -1):
        fields.append(f"Ref($money, {i})/($money+1e-12)")
        names.append(f"EXT_MONEY{i}")
    fields.append("$money/($money+1e-12)")
    names.append("EXT_MONEY0")
    return fields, names
