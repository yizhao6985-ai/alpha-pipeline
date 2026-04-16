"""daily_basic 基本面特征。"""
from __future__ import annotations


def fundamental_feature_config() -> tuple[list[str], list[str]]:
    """daily_basic：换手、量比、市值及估值（与 ``scripts.build_qlib.to_qlib.DAILY_BASIC_COLS`` 一致）。"""
    fields: list[str] = []
    names: list[str] = []

    fields += [
        "$turnover_rate",
        "$volume_ratio",
        "Log($circ_mv + 1)",
        "Log($total_mv + 1)",
        "$pe",
        "$pe_ttm",
        "$pb",
        "$ps",
        "$ps_ttm",
        "$dv_ratio",
    ]
    names += [
        "RAW_TURNOVER_RATE",
        "RAW_VOL_RATIO_BASIC",
        "RAW_LOG_CIRC_MV",
        "RAW_LOG_TOTAL_MV",
        "RAW_PE",
        "RAW_PE_TTM",
        "RAW_PB",
        "RAW_PS",
        "RAW_PS_TTM",
        "RAW_DV_RATIO",
    ]

    return fields, names
