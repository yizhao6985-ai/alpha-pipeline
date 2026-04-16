"""由参数构建训练用 ``AlphaPipelineRawFields`` Handler。"""
from __future__ import annotations

from typing import Any

from scripts.qlib.handler.alpha_pipeline_handler import AlphaPipelineRawFields
from scripts.qlib.handler.label import DEFAULT_LABEL_EXPR
from scripts.qlib.handler.processors import default_infer_processors


def build_training_handler(
    *,
    instruments: str = "all",
    fit_start_time: str,
    fit_end_time: str,
    data_start_time: str,
    data_end_time: str,
    label_expr: str = DEFAULT_LABEL_EXPR,
    feature_config: tuple[list[str], list[str]] | None = None,
) -> AlphaPipelineRawFields:
    """构建 DataHandler：原始字段特征 + DropnaLabel + 标签截面 z-score。

    ``feature_config`` 为 ``None`` 时使用 Handler 默认特征（见 ``handler.features.lab_fixed_features``）。
    """
    learn_processors: list[dict[str, Any]] = [
        {"class": "DropnaLabel"},
        {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
    ]
    infer_processors = default_infer_processors(fit_start_time, fit_end_time)
    label_cfg: tuple[list[str], list[str]] = ([label_expr], ["LABEL0"])
    return AlphaPipelineRawFields(
        instruments=instruments,
        start_time=data_start_time,
        end_time=data_end_time,
        fit_start_time=fit_start_time,
        fit_end_time=fit_end_time,
        infer_processors=infer_processors,
        learn_processors=learn_processors,
        feature_config=feature_config,
        label=label_cfg,
    )
