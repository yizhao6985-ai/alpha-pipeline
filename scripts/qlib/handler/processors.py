"""DataHandler 的 learn / infer 侧 processor 列表。"""
from __future__ import annotations

from typing import Any

FeatureNormMode = str  # "robust_zscore" | "cs_rank"


def default_learn_processors() -> list[dict[str, Any]]:
    """学习侧：去掉标签缺失样本，对标签做截面 z-score。"""
    return [
        {"class": "DropnaLabel"},
        {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
    ]


def default_infer_processors(
    fit_start_time: str,
    fit_end_time: str,
    *,
    feature_norm: FeatureNormMode = "robust_zscore",
) -> list[dict[str, Any]]:
    """推理侧：去 inf、填 NaN；默认 RobustZScoreNorm；可选 CSRankNorm（冲 Rank IC 时试）。"""
    common: list[dict[str, Any]] = [
        {"class": "ProcessInf", "kwargs": {}},
        {
            "class": "Fillna",
            "kwargs": {"fields_group": "feature", "fill_value": 0},
        },
    ]
    if feature_norm == "cs_rank":
        common.append({"class": "CSRankNorm", "kwargs": {"fields_group": "feature"}})
    else:
        common.append(
            {
                "class": "RobustZScoreNorm",
                "kwargs": {
                    "fit_start_time": fit_start_time,
                    "fit_end_time": fit_end_time,
                    "fields_group": "feature",
                    "clip_outlier": True,
                },
            }
        )
    return common
