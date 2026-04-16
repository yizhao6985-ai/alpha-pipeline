"""扩展价量特征（与 Alpha158 互补）。"""
from __future__ import annotations

# 与下游子表达式共用字面量，便于 merge 时按表达式去重
_RET1 = "$close / Ref($close, 1) - 1"


def raw_market_feature_config() -> tuple[list[str], list[str]]:
    """价量：基础列 + 与 Alpha158 互补的 TR/波动、日内位置、额量变化等。"""
    fields: list[str] = []
    names: list[str] = []

    fields += [
        _RET1,
        "($high - $low) / ($close + 1e-12)",
        "Log($volume + 1)",
        "Log($money + 1)",
    ]
    names += [
        "RAW_RET1",
        "RAW_HL_RANGE",
        "RAW_LOG_VOL",
        "RAW_LOG_MONEY",
    ]

    fields += [
        "($open - Ref($close, 1)) / (Ref($close, 1) + 1e-12)",
        "(Ref($open, 1) - Ref($close, 2)) / (Ref($close, 2) + 1e-12)",
    ]
    names += [
        "RAW_GAP_TODAY",
        "RAW_ON_RET_PREV",
    ]

    _tr = (
        "Greater(Greater($high - $low, Abs($high - Ref($close, 1))), "
        "Abs($low - Ref($close, 1)))"
    )
    fields += [
        f"Mean(({_tr}), 14) / ($close + 1e-12)",
        f"Mean(({_tr}), 20) / ($close + 1e-12)",
    ]
    names += ["RAW_TR_MEAN14_NORM", "RAW_TR_MEAN20_NORM"]

    fields += [
        "Mean((Power(Log($high / ($low + 1e-12)), 2)), 20)",
    ]
    names += ["RAW_PK_LOGHL2_M20"]

    fields += [
        f"Std(({_RET1}), 5) / (Std(({_RET1}), 60) + 1e-12)",
    ]
    names += ["RAW_STDRATIO_RET_5_60"]

    fields += [
        f"EMA(Power(({_RET1}), 2), 20)",
    ]
    names += ["RAW_EWMA_SQRET20"]

    fields += [
        "($close - $low) / ($high - $low + 1e-12)",
        "($close - $open) / ($high - $low + 1e-12)",
    ]
    names += ["RAW_CLV", "RAW_OC_IN_HL"]

    _refc1 = "Ref($close, 1)"
    fields += [
        f"(($open - {_refc1}) / (({_refc1}) + 1e-12)) / "
        f"(($high - $low) / (({_refc1}) + 1e-12) + 1e-12)",
    ]
    names += ["RAW_GAP_REL_RANGE"]

    fields += [
        "Log($volume + 1) - Ref(Log($volume + 1), 1)",
        "Log($money + 1) - Ref(Log($money + 1), 1)",
        "($volume - Mean($volume, 20)) / (Mean($volume, 20) + 1e-12)",
    ]
    names += ["RAW_DLOG_VOL1", "RAW_DLOG_MONEY1", "RAW_VOL_EXCESS20"]

    return fields, names
