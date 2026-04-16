"""LightGBM gain 重要度：将默认 ``Column_*`` 索引换为与训练矩阵一致的特征名。"""
from __future__ import annotations

from typing import Any

import pandas as pd
from qlib.data.dataset.handler import DataHandlerLP


def _col_to_label(c: Any) -> str:
    if isinstance(c, tuple):
        return "|".join(str(p) for p in c)
    return str(c)


def _train_feature_column_labels(dataset: Any) -> list[str] | None:
    try:
        x = dataset.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_L)
    except Exception:  # noqa: BLE001
        try:
            x = dataset.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_I)
        except Exception:  # noqa: BLE001
            return None
    return [_col_to_label(c) for c in x.columns]


def _remap_importance_index(fi: pd.Series, labels: list[str]) -> pd.Series:
    if len(labels) != len(fi):
        return fi

    def map_one(idx: Any) -> str:
        s = str(idx)
        if not s.startswith("Column_"):
            return s
        try:
            j = int(s[7:], 10)
        except ValueError:
            return s
        if 0 <= j < len(labels):
            return labels[j]
        return s

    return pd.Series(fi.values, index=pd.Index([map_one(i) for i in fi.index]))


def order_indices_by_gain(names: list[str], gain: dict[str, float]) -> list[int]:
    """按 gain 降序排特征下标。键可为 handler 列名，或 LightGBM 的 ``Column_{i}``（与矩阵列序一致）。"""
    scored: list[tuple[float, int]] = []
    for i, n in enumerate(names):
        g = gain.get(str(n))
        if g is None:
            g = gain.get(f"Column_{i}", 0.0)
        scored.append((float(g), i))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in scored]


def feature_importance_for_export(
    model: Any,
    *,
    dataset: Any | None = None,
    column_labels: list[str] | None = None,
    importance_type: str = "gain",
) -> pd.Series | None:
    """导出用重要度序列：索引为特征名（与 handler 列名或 ``column_labels`` 一致）。

    - 提供 ``dataset`` 时：从 ``train`` 段 feature 矩阵读取列名（与 LGB 训练一致）。
    - 或提供 ``column_labels``（与训练时特征列顺序等长），例如 sweep 里已有 ``full_names``。
    - 长度对不上或无法解析时，保留 LightGBM 原始 ``Column_*`` 索引。
    - 若底层 ``get_feature_importance`` 返回 ``None``，则本函数返回 ``None``。
    """
    fi = model.get_feature_importance(importance_type=importance_type)
    if fi is None:
        return None
    if column_labels is not None:
        return _remap_importance_index(fi, column_labels)
    if dataset is not None:
        lab = _train_feature_column_labels(dataset)
        if lab is not None and len(lab) == len(fi):
            return _remap_importance_index(fi, lab)
    return fi
