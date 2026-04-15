"""DataHandler infer 侧 processor 列表。"""
from __future__ import annotations

from typing import Any


def default_infer_processors(fit_start_time: str, fit_end_time: str) -> list[dict[str, Any]]:
    """推理侧：去 inf、填 NaN、截面鲁棒标准化。"""
    return [
        {"class": "ProcessInf", "kwargs": {}},
        {
            "class": "Fillna",
            "kwargs": {"fields_group": "feature", "fill_value": 0},
        },
        {
            "class": "RobustZScoreNorm",
            "kwargs": {
                "fit_start_time": fit_start_time,
                "fit_end_time": fit_end_time,
                "fields_group": "feature",
                "clip_outlier": True,
            },
        },
    ]
