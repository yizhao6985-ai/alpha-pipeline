"""筹码分布相关特征。"""
from __future__ import annotations


def chip_feature_config() -> tuple[list[str], list[str]]:
    """筹码分布 + 加权均价相对收盘偏离。"""
    fields: list[str] = []
    names: list[str] = []

    fields += [
        "($close - $cost_50pct) / ($close + 1e-12)",
        "($cost_85pct - $cost_15pct) / ($close + 1e-12)",
        "$winner_rate",
        "($close - $his_low) / ($his_high - $his_low + 1e-12)",
    ]
    names += [
        "RAW_CHIP_BIAS50",
        "RAW_CHIP_WIDTH_85_15",
        "RAW_WINNER_RATE",
        "RAW_HIS_RANGE_POS",
    ]

    fields += [
        "($close - $cost_5pct) / ($close + 1e-12)",
        "($close - $cost_95pct) / ($close + 1e-12)",
    ]
    names += [
        "RAW_CHIP_COST5_BIAS",
        "RAW_CHIP_BIAS95",
    ]

    fields += [
        "($close - $weight_avg) / ($close + 1e-12)",
    ]
    names += [
        "RAW_WAVG_BIAS",
    ]

    return fields, names
