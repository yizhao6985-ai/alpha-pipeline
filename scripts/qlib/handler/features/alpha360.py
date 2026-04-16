"""
Alpha360：60 日 OHLCVWAP + 成交量相对当日收盘/成交量的归一化堆叠（与 Qlib ``Alpha360DL`` 一致）。

列名加 ``A360_`` 前缀，便于与 Alpha158 的 ``CLOSE0`` 等同名区分；与 Alpha158 合并时会按 **表达式** 去重，
避免与 Alpha158 已含的重叠滞后项重复入模。
"""
from __future__ import annotations

from qlib.contrib.data.loader import Alpha360DL


def alpha360_stacked_feature_config() -> tuple[list[str], list[str]]:
    """Alpha360 ``(fields, names)``，名称带 ``A360_`` 前缀。"""
    fields, names = Alpha360DL.get_feature_config()
    return fields, [f"A360_{n}" for n in names]
