"""
固定维度训练特征：(field_expr, column_name)。
不读 CSV、不做动态筛选；训练仅使用本表。

元组 **LAB_FIXED_FEATURES** 内顺序即训练列序，勿随意改动；分类说明以元组内分块注释为准。
"""
from __future__ import annotations

# fmt: off
LAB_FIXED_FEATURES: tuple[tuple[str, str], ...] = (
    # --- MKT_RAW | 对数成交额 ---
    ("Log($money + 1)", "MKT_RAW_LOG_MONEY"),
    # --- A158 | 区间 RSV、K 线型态（KSFT）---
    ("($close-Min($low, 60))/(Max($high, 60)-Min($low, 60)+1e-12)", "A158_RSV60"),
    ("(2*$close-$high-$low)/$open", "A158_KSFT"),
    # --- MKT_RAW | 对数成交量 ---
    ("Log($volume + 1)", "MKT_RAW_LOG_VOL"),
    # --- A158 | 极值比、K 线（HIGH0/LOW0、KSFT2）、残差 ---
    ("Max($high, 60)/$close", "A158_MAX60"),
    ("$high/$close", "A158_HIGH0"),
    ("(2*$close-$high-$low)/($high-$low+1e-12)", "A158_KSFT2"),
    ("Resi($close, 5)/$close", "A158_RESI5"),
    ("$low/$close", "A158_LOW0"),
    # --- MKT_RAW | 1 日收益 ---
    ("$close / Ref($close, 1) - 1", "MKT_RAW_RET1"),
    # --- A158 | 60 日低价极值比 ---
    ("Min($low, 60)/$close", "A158_MIN60"),
    # --- CHIP_RAW | 历史筹码区间位置 ---
    ("($close - $his_low) / ($his_high - $his_low + 1e-12)", "CHIP_RAW_HIS_RANGE_POS"),
    # --- A158 | K 线（KUP）、VWAP ---
    ("($high-Greater($open, $close))/$open", "A158_KUP"),
    ("$vwap/$close", "A158_VWAP0"),
    # --- FUND_RAW | 量比、对数流通市值 ---
    ("$volume_ratio", "FUND_RAW_VOL_RATIO_BASIC"),
    ("Log($circ_mv + 1)", "FUND_RAW_LOG_CIRC_MV"),
    # --- A158 | 残差、下影（KLOW2）---
    ("Resi($close, 10)/$close", "A158_RESI10"),
    ("(Less($open, $close)-$low)/($high-$low+1e-12)", "A158_KLOW2"),
    # --- FUND_RAW | 对数总市值 ---
    ("Log($total_mv + 1)", "FUND_RAW_LOG_TOTAL_MV"),
    # --- A158 | 均线 MA20、量相对波动 VSTD10 ---
    ("Mean($close, 20)/$close", "A158_MA20"),
    ("Std($volume, 10)/($volume+1e-12)", "A158_VSTD10"),
    # --- MKT_RAW | 多窗真实波幅类均值、log 高低波动结构 ---
    ("Mean((Greater(Greater($high - $low, Abs($high - Ref($close, 1))), Abs($low - Ref($close, 1)))), 20) / ($close + 1e-12)", "MKT_RAW_TR_MEAN20_NORM"),
    ("Mean((Power(Log($high / ($low + 1e-12)), 2)), 20)", "MKT_RAW_PK_LOGHL2_M20"),
    # --- A158 | 30 日价格趋势 R² ---
    ("Rsquare($close, 30)", "A158_RSQR30"),
    # --- MKT_RAW | 跳空相对振幅 ---
    ("(($open - Ref($close, 1)) / ((Ref($close, 1)) + 1e-12)) / (($high - $low) / ((Ref($close, 1)) + 1e-12) + 1e-12)", "MKT_RAW_GAP_REL_RANGE"),
    # --- A158 | 实体、下影（KLOW）---
    ("($close-$open)/$open", "A158_KMID"),
    ("(Less($open, $close)-$low)/$open", "A158_KLOW"),
    # --- MKT_RAW | 短长窗收益波动比、14 日 TR 均值 ---
    ("Std(($close / Ref($close, 1) - 1), 5) / (Std(($close / Ref($close, 1) - 1), 60) + 1e-12)", "MKT_RAW_STDRATIO_RET_5_60"),
    ("Mean((Greater(Greater($high - $low, Abs($high - Ref($close, 1))), Abs($low - Ref($close, 1)))), 14) / ($close + 1e-12)", "MKT_RAW_TR_MEAN14_NORM"),
    # --- A158 | 收益波动 STD60、量均线 VMA10、低价 MIN10 ---
    ("Std($close, 60)/$close", "A158_STD60"),
    ("Mean($volume, 10)/($volume+1e-12)", "A158_VMA10"),
    ("Min($low, 10)/$close", "A158_MIN10"),
    # --- MKT_RAW | 平方收益 EMA、隔夜开盘收益 ---
    ("EMA(Power(($close / Ref($close, 1) - 1), 2), 20)", "MKT_RAW_EWMA_SQRET20"),
    ("($open - Ref($close, 1)) / (Ref($close, 1) + 1e-12)", "MKT_RAW_GAP_TODAY"),
    # --- A158 | 短窗均线/极值/量（MA5、MAX5、VMA5、VSTD5、STD20/5）---
    ("Mean($volume, 5)/($volume+1e-12)", "A158_VMA5"),
    ("Mean($close, 5)/$close", "A158_MA5"),
    ("Max($high, 5)/$close", "A158_MAX5"),
    ("Std($volume, 5)/($volume+1e-12)", "A158_VSTD5"),
    ("Std($close, 20)/$close", "A158_STD20"),
    ("Std($close, 5)/$close", "A158_STD5"),
    # --- FUND_RAW | 换手率 ---
    ("$turnover_rate", "FUND_RAW_TURNOVER_RATE"),
    # --- CHIP_RAW | 收盘相对 5% 成本带 ---
    ("($close - $cost_5pct) / ($close + 1e-12)", "CHIP_RAW_CHIP_COST5_BIAS"),
    # --- MKT_RAW | 昨开相对前收 ---
    ("(Ref($open, 1) - Ref($close, 2)) / (Ref($close, 2) + 1e-12)", "MKT_RAW_ON_RET_PREV"),
    # --- A158 | ROC5、STD30、价量 CORR30 ---
    ("Ref($close, 5)/$close", "A158_ROC5"),
    ("Std($close, 30)/$close", "A158_STD30"),
    ("Corr($close, Log($volume+1), 30)", "A158_CORR30"),
    # --- CHIP_RAW | 85–15% 筹码带宽度 ---
    ("($cost_85pct - $cost_15pct) / ($close + 1e-12)", "CHIP_RAW_CHIP_WIDTH_85_15"),
    # --- A158 | 价格斜率 BETA、筹码 95% 偏置、残差 RESI20 ---
    ("Slope($close, 60)/$close", "A158_BETA60"),
    ("Slope($close, 20)/$close", "A158_BETA20"),
    ("($close - $cost_95pct) / ($close + 1e-12)", "CHIP_RAW_CHIP_BIAS95"),
    ("Resi($close, 20)/$close", "A158_RESI20"),
    # --- A158 | BETA10、上影占比 KUP2、ROC60、RANK60、RSV20 ---
    ("Slope($close, 10)/$close", "A158_BETA10"),
    ("($high-Greater($open, $close))/($high-$low+1e-12)", "A158_KUP2"),
    ("Ref($close, 60)/$close", "A158_ROC60"),
    ("Rank($close, 60)", "A158_RANK60"),
    ("($close-Min($low, 20))/(Max($high, 20)-Min($low, 20)+1e-12)", "A158_RSV20"),
    # --- MKT_RAW | 当日振幅/收盘 ---
    ("($high - $low) / ($close + 1e-12)", "MKT_RAW_HL_RANGE"),
    # --- FUND_RAW | 市净率 ---
    ("$pb", "FUND_RAW_PB"),
    # --- MKT_RAW | 量对数一阶差分 ---
    ("Log($volume + 1) - Ref(Log($volume + 1), 1)", "MKT_RAW_DLOG_VOL1"),
    # --- A158 | 价量相关 CORD60、VMA60、量方向 VSUMP5、多窗 RSV ---
    ("Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 60)", "A158_CORD60"),
    ("Mean($volume, 60)/($volume+1e-12)", "A158_VMA60"),
    ("Sum(Greater($volume-Ref($volume, 1), 0), 5)/(Sum(Abs($volume-Ref($volume, 1)), 5)+1e-12)", "A158_VSUMP5"),
    ("($close-Min($low, 5))/(Max($high, 5)-Min($low, 5)+1e-12)", "A158_RSV5"),
    ("($close-Min($low, 30))/(Max($high, 30)-Min($low, 30)+1e-12)", "A158_RSV30"),
    # --- A158 | ROC10、VSTD30、CORD5、RSQR、量不对称 VSUM ---
    ("Ref($close, 10)/$close", "A158_ROC10"),
    ("Std($volume, 30)/($volume+1e-12)", "A158_VSTD30"),
    ("Corr($close/Ref($close,1), Log($volume/Ref($volume, 1)+1), 5)", "A158_CORD5"),
    ("Rsquare($close, 10)", "A158_RSQR10"),
    ("Rsquare($close, 20)", "A158_RSQR20"),
    ("Sum(Greater(Ref($volume, 1)-$volume, 0), 10)/(Sum(Abs($volume-Ref($volume, 1)), 10)+1e-12)", "A158_VSUMN10"),
    ("Sum(Greater($volume-Ref($volume, 1), 0), 60)/(Sum(Abs($volume-Ref($volume, 1)), 60)+1e-12)", "A158_VSUMP60"),
    # --- FUND_RAW | 市盈率 ---
    ("$pe", "FUND_RAW_PE"),
    # --- A158 | 加权量波动 WVMA5、MA30 ---
    ("Std(Abs($close/Ref($close, 1)-1)*$volume, 5)/(Mean(Abs($close/Ref($close, 1)-1)*$volume, 5)+1e-12)", "A158_WVMA5"),
    ("Mean($close, 30)/$close", "A158_MA30"),
)
# fmt: on

DEFAULT_HEAD_FEATURES: int = len(LAB_FIXED_FEATURES)


def lab_fixed_feature_config() -> tuple[list[str], list[str]]:
    """与 :data:`LAB_FIXED_FEATURES` 等长的 ``(fields, names)``。"""
    return [p[0] for p in LAB_FIXED_FEATURES], [p[1] for p in LAB_FIXED_FEATURES]


assert len(LAB_FIXED_FEATURES) == 74
