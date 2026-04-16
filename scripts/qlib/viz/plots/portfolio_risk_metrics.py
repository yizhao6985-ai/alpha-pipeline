"""超额收益风险指标表（CSV）。"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from qlib.contrib.evaluate import risk_analysis


def build_risk_metrics_dataframe(report_normal: pd.DataFrame) -> pd.DataFrame:
    need = {"return", "bench", "cost"}
    if not need <= set(report_normal.columns):
        missing = need - set(report_normal.columns)
        raise ValueError(f"report_normal 缺少列: {sorted(missing)}")
    r = pd.to_numeric(report_normal["return"], errors="coerce").fillna(0.0)
    b = pd.to_numeric(report_normal["bench"], errors="coerce").fillna(0.0)
    c = pd.to_numeric(report_normal["cost"], errors="coerce").fillna(0.0)
    ex_wo = r - b
    ex_w = ex_wo - c
    wo = risk_analysis(ex_wo, freq="day")
    w = risk_analysis(ex_w, freq="day")
    merged = pd.concat([wo, w], axis=1)
    merged.columns = ["excess_return_without_cost", "excess_return_with_cost"]
    merged.index.name = "metric"
    return merged


def write_portfolio_risk_metrics_csv(report_normal: pd.DataFrame, path: Path) -> None:
    metrics = build_risk_metrics_dataframe(report_normal)
    path.parent.mkdir(parents=True, exist_ok=True)
    metrics.reset_index().to_csv(path, index=False)
