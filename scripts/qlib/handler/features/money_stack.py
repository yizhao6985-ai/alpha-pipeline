"""成交额归一化堆叠特征（相对当日成交额）。"""
from __future__ import annotations

_DEFAULT_STACK_DAYS = 20


def money_amount_stack_feature_config(*, stack_days: int = _DEFAULT_STACK_DAYS) -> tuple[list[str], list[str]]:
    """成交额堆叠：``EXT_MONEY{k}`` 为 ``Ref($money,k)/当日额``（k>0），``EXT_MONEY0`` 恒为 1。

    ``stack_days``：堆叠长度（含当日）。默认 20 以降低与 Alpha 族的共线性与计算量；
    ``stack_days=60`` 与历史「60 档」形式一致。
    """
    if stack_days < 1:
        raise ValueError("stack_days 须 >= 1")
    fields: list[str] = []
    names: list[str] = []
    for i in range(stack_days - 1, 0, -1):
        fields.append(f"Ref($money, {i})/($money + 1e-12)")
        names.append(f"EXT_MONEY{i}")
    fields.append("$money/($money + 1e-12)")
    names.append("EXT_MONEY0")
    return fields, names
