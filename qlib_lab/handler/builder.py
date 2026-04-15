"""由参数构建训练用 ``QuantFoundryRawFields`` Handler。"""
from __future__ import annotations

from typing import Any

from qlib_lab.handler.processors import default_infer_processors
from qlib_lab.handler.quant_foundry import QuantFoundryRawFields

from qlib_lab.handler.label import DEFAULT_LABEL_EXPR


def build_training_handler(
    *,
    instruments: str = "all",
    fit_start_time: str,
    fit_end_time: str,
    data_start_time: str,
    data_end_time: str,
    label_expr: str = DEFAULT_LABEL_EXPR,
    feature_config: tuple[list[str], list[str]] | None = None,
) -> QuantFoundryRawFields:
    """构建 DataHandler：原始字段特征 + DropnaLabel + 标签截面 z-score。

    ``feature_config`` 为 ``None`` 时使用 Handler 默认特征（当前为 gain 前 508 列裁剪集）。
    """
    learn_processors: list[dict[str, Any]] = [
        {"class": "DropnaLabel"},
        {"class": "CSZScoreNorm", "kwargs": {"fields_group": "label"}},
    ]
    infer_processors = default_infer_processors(fit_start_time, fit_end_time)
    label_cfg: tuple[list[str], list[str]] = ([label_expr], ["LABEL0"])
    return QuantFoundryRawFields(
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
