"""
固定维度训练特征：(field_expr, column_name)。
不读 CSV、不做动态筛选；训练仅使用本表。

元组 **LAB_FIXED_FEATURES** 内顺序即训练列序。历史版本曾按 ``feature_importance.csv``
的 ``importance_gain`` 排序；当前为 **55 维**（已移除筹码字段 ``CHIP_RAW_*``）。
每项上方的 ``# --- … ---`` 为语义分组（MKT_RAW / A158 / FUND_RAW），与列序独立，仅便于阅读。

**消融预设**（CLI ``--feature-preset``）：在固定 55 维上按组剔除，便于对照样本外 IC。

- ``full``：全部 55 列（默认）。
- ``no_overnight``：去掉隔夜/跳空显式项（``MKT_RAW_GAP_*``、``MKT_RAW_ON_RET_PREV`` 共 3 列）。
- ``no_fund``：去掉全部 ``FUND_RAW_*``（基本面/市值量比等）。
- ``no_mkt``：去掉全部 ``MKT_RAW_*``（仅保留 ``A158_*`` 与 ``FUND_RAW_*``）。

兼容旧 CLI 值：``lean`` 视为 ``no_overnight``。
"""

from __future__ import annotations

# fmt: off
LAB_FIXED_FEATURES: tuple[tuple[str, str], ...] = (
    # --- 列序：importance_gain 降序（见 qlib_runs/plots/feature_importance.csv）；下行注释为语义分组 ---
    # --- A158 | 区间 RSV、K 线型态（KSFT）---
    ("($close-Min($low, 60))/(Max($high, 60)-Min($low, 60)+1e-12)", "A158_RSV60"),
    # --- MKT_RAW | 对数成交额 ---
    ("Log($money + 1)", "MKT_RAW_LOG_MONEY"),
    # --- MKT_RAW | 对数成交量 ---
    ("Log($volume + 1)", "MKT_RAW_LOG_VOL"),
    # --- A158 | 极值比、K 线（HIGH0/LOW0、KSFT2）、残差 ---
    ("$low/$close", "A158_LOW0"),
    ("$high/$close", "A158_HIGH0"),
    ("(2*$close-$high-$low)/$open", "A158_KSFT"),
    ("Max($high, 60)/$close", "A158_MAX60"),
    # --- A158 | K 线（KUP）、VWAP ---
    ("$vwap/$close", "A158_VWAP0"),
    # --- MKT_RAW | 1 日收益 ---
    ("$close / Ref($close, 1) - 1", "MKT_RAW_RET1"),
    # --- A158 | 极值比、K 线（HIGH0/LOW0、KSFT2）、残差 ---
    ("Resi($close, 5)/$close", "A158_RESI5"),
    # --- FUND_RAW | 量比、对数流通市值 ---
    ("Log($circ_mv + 1)", "FUND_RAW_LOG_CIRC_MV"),
    ("$volume_ratio", "FUND_RAW_VOL_RATIO_BASIC"),
    # --- A158 | 60 日低价极值比 ---
    ("Min($low, 60)/$close", "A158_MIN60"),
    # --- A158 | K 线（KUP）、VWAP ---
    ("($high-Greater($open, $close))/$open", "A158_KUP"),
    # --- A158 | 极值比、K 线（HIGH0/LOW0、KSFT2）、残差 ---
    ("(2*$close-$high-$low)/($high-$low+1e-12)", "A158_KSFT2"),
    # --- A158 | 残差、下影（KLOW2）---
    ("Resi($close, 10)/$close", "A158_RESI10"),
    # --- FUND_RAW | 对数总市值 ---
    ("Log($total_mv + 1)", "FUND_RAW_LOG_TOTAL_MV"),
    # --- MKT_RAW | 跳空相对振幅 ---
    ("(($open - Ref($close, 1)) / ((Ref($close, 1)) + 1e-12)) / (($high - $low) / ((Ref($close, 1)) + 1e-12) + 1e-12)", "MKT_RAW_GAP_REL_RANGE"),
    # --- A158 | 残差、下影（KLOW2）---
    ("(Less($open, $close)-$low)/($high-$low+1e-12)", "A158_KLOW2"),
    # --- A158 | 均线 MA20、量相对波动 VSTD10 ---
    ("Mean($close, 20)/$close", "A158_MA20"),
    # --- A158 | 短窗均线/极值/量（MA5、MAX5、VMA5、VSTD5、STD20/5）---
    ("Mean($volume, 5)/($volume+1e-12)", "A158_VMA5"),
    # --- A158 | 加权量波动 WVMA5、MA30 ---
    ("Mean($close, 30)/$close", "A158_MA30"),
    # --- A158 | 短窗均线/极值/量（MA5、MAX5、VMA5、VSTD5、STD20/5）---
    ("Mean($close, 5)/$close", "A158_MA5"),
    # --- A158 | 价量相关 CORD60、VMA60、量方向 VSUMP5、多窗 RSV ---
    ("($close-Min($low, 5))/(Max($high, 5)-Min($low, 5)+1e-12)", "A158_RSV5"),
    # --- MKT_RAW | 平方收益 EMA ---
    ("EMA(Power(($close / Ref($close, 1) - 1), 2), 20)", "MKT_RAW_EWMA_SQRET20"),
    # --- A158 | 收益波动 STD60、量均线 VMA10、低价 MIN10 ---
    ("Mean($volume, 10)/($volume+1e-12)", "A158_VMA10"),
    # --- MKT_RAW | 多窗真实波幅类均值（归一）---
    ("Mean((Greater(Greater($high - $low, Abs($high - Ref($close, 1))), Abs($low - Ref($close, 1)))), 20) / ($close + 1e-12)", "MKT_RAW_TR_MEAN20_NORM"),
    # --- A158 | 均线 MA20、量相对波动 VSTD10 ---
    ("Std($volume, 10)/($volume+1e-12)", "A158_VSTD10"),
    # --- A158 | 收益波动 STD60、量均线 VMA10、低价 MIN10 ---
    ("Std($close, 60)/$close", "A158_STD60"),
    # --- A158 | ROC5、STD30、价量 CORR30 ---
    ("Ref($close, 5)/$close", "A158_ROC5"),
    # --- A158 | 30 日价格趋势 R² ---
    ("Rsquare($close, 30)", "A158_RSQR30"),
    # --- A158 | BETA10、上影占比 KUP2、ROC60、RANK60、RSV20 ---
    ("Slope($close, 10)/$close", "A158_BETA10"),
    # --- A158 | ROC10、VSTD30、CORD5、RSQR、量不对称 VSUM ---
    ("Sum(Greater($volume-Ref($volume, 1), 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)", "A158_VSUMP60"),
    ("Corr($close, Log($volume+1), 30)", "A158_CORR30"),
    # --- A158 | 实体、下影（KLOW）---
    ("(Less($open, $close)-$low)/$open", "A158_KLOW"),
    # --- A158 | BETA10、上影占比 KUP2、ROC60、RANK60、RSV20 ---
    ("($close-Min($low, 20))/(Max($high, 20)-Min($low, 20)+1e-12)", "A158_RSV20"),
    # --- A158 | 实体、下影（KLOW）---
    ("($close-$open)/$open", "A158_KMID"),
    # --- A158 | 价格斜率 BETA、残差 RESI20 ---
    ("Slope($close, 20)/$close", "A158_BETA20"),
    # --- A158 | ROC5、STD30、价量 CORR30 ---
    ("Std($close, 30)/$close", "A158_STD30"),
    # --- A158 | 收益波动 STD60、量均线 VMA10、低价 MIN10 ---
    ("Min($low, 10)/$close", "A158_MIN10"),
    # --- A158 | 短窗均线/极值/量（MA5、MAX5、VMA5、VSTD5、STD20/5）---
    ("Std($volume, 5)/($volume+1e-12)", "A158_VSTD5"),
    # --- A158 | 价格斜率 BETA60 ---
    ("Slope($close, 60)/$close", "A158_BETA60"),
    # --- A158 | 价量相关 CORD60、VMA60、量方向 VSUMP5、多窗 RSV ---
    ("($close-Min($low, 30))/(Max($high, 30)-Min($low, 30)+1e-12)", "A158_RSV30"),
    # --- MKT_RAW | 短长窗收益波动比、14 日 TR 均值 ---
    ("Std(($close / Ref($close, 1) - 1), 5) / (Std(($close / Ref($close, 1) - 1), 60) + 1e-12)", "MKT_RAW_STDRATIO_RET_5_60"),
    # --- MKT_RAW | 隔夜开盘跳空 ---
    ("($open - Ref($close, 1)) / (Ref($close, 1) + 1e-12)", "MKT_RAW_GAP_TODAY"),
    # --- MKT_RAW | 昨开相对前收 ---
    ("(Ref($open, 1) - Ref($close, 2)) / (Ref($close, 2) + 1e-12)", "MKT_RAW_ON_RET_PREV"),
    # --- A158 | 短窗均线/极值/量（MA5、MAX5、VMA5、VSTD5、STD20/5）---
    ("Std($close, 20)/$close", "A158_STD20"),
    # --- MKT_RAW | 量对数一阶差分 ---
    ("Log($volume + 1) - Ref(Log($volume + 1), 1)", "MKT_RAW_DLOG_VOL1"),
    # --- A158 | 残差 RESI20 ---
    ("Resi($close, 20)/$close", "A158_RESI20"),
    # --- A158 | 价量相关 CORD60、VMA60、量方向 VSUMP5、多窗 RSV ---
    ("Sum(Greater($volume-Ref($volume, 1), 0), 5)/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)", "A158_VSUMP5"),
    # --- A158 | ROC10、VSTD30、CORD5、RSQR、量不对称 VSUM ---
    ("Ref($close, 10)/$close", "A158_ROC10"),
    # --- MKT_RAW | 当日振幅/收盘 ---
    ("($high - $low) / ($close + 1e-12)", "MKT_RAW_HL_RANGE"),
    # --- A158 | BETA10、上影占比 KUP2、ROC60、RANK60、RSV20 ---
    ("($high-Greater($open, $close))/($high-$low+1e-12)", "A158_KUP2"),
    # --- MKT_RAW | 短长窗收益波动比、14 日 TR 均值 ---
    ("Mean((Greater(Greater($high - $low, Abs($high - Ref($close, 1))), Abs($low - Ref($close, 1)))), 14) / ($close + 1e-12)", "MKT_RAW_TR_MEAN14_NORM"),
    # --- MKT_RAW | 20 日超额动量相对 20 日波动（Sharpe 风格）---
    ("($close/Mean($close,20)-1) / (Std($close,20)/$close+1e-12)", "MKT_RAW_MOM20_OVER_VOL20"),
)
# fmt: on

DEFAULT_HEAD_FEATURES: int = len(LAB_FIXED_FEATURES)


def lab_fixed_feature_config() -> tuple[list[str], list[str]]:
    """与 :data:`LAB_FIXED_FEATURES` 等长的 ``(fields, names)``。"""
    return [p[0] for p in LAB_FIXED_FEATURES], [p[1] for p in LAB_FIXED_FEATURES]


FEATURE_PRESET_CHOICES: tuple[str, ...] = (
    "full",
    "no_overnight",
    "no_fund",
    "no_mkt",
    "lean",
)

# no_overnight：与 T+1 收盘标签错位的隔夜显式因子（消融用）
_OVERNIGHT_FEATURE_NAMES: frozenset[str] = frozenset(
    {
        "MKT_RAW_GAP_REL_RANGE",
        "MKT_RAW_GAP_TODAY",
        "MKT_RAW_ON_RET_PREV",
    }
)

_SUBSET_PRESETS: frozenset[str] = frozenset(
    {
        "no_overnight",
        "no_fund",
        "no_mkt",
    }
)


def lab_fixed_feature_config_for_preset(preset: str) -> tuple[list[str], list[str]]:
    """按预设从 :data:`LAB_FIXED_FEATURES` 派生子集 ``(fields, names)``。"""
    p = (preset or "full").strip().lower()
    _legacy = {"lean": "no_overnight"}
    p = _legacy.get(p, p)
    if p == "full":
        return lab_fixed_feature_config()
    if p not in _SUBSET_PRESETS:
        raise ValueError(
            f"未知 feature-preset: {preset!r}，可选 {FEATURE_PRESET_CHOICES}"
        )

    pairs = list(LAB_FIXED_FEATURES)
    if p == "no_overnight":
        pairs = [x for x in pairs if x[1] not in _OVERNIGHT_FEATURE_NAMES]
    if p == "no_fund":
        pairs = [x for x in pairs if not x[1].startswith("FUND_RAW")]
    if p == "no_mkt":
        pairs = [x for x in pairs if not x[1].startswith("MKT_RAW")]
    if not pairs:
        raise ValueError(f"feature-preset={preset!r} 剔除后为空")
    return [x[0] for x in pairs], [x[1] for x in pairs]


assert len(LAB_FIXED_FEATURES) == 55
