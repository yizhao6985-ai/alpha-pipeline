"""按 Dataset 分段计算 IC / Rank IC（与 SigAna 一致：标签用 DK_R 原始收益）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from qlib.contrib.eva.alpha import calc_ic
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP

from scripts.qlib.viz.plots.ic_stats import summarize_ic_like_series


def compute_segment_ic_metrics(
    model: Any,
    dataset: DatasetH,
    *,
    segments: tuple[str, ...] = ("train", "valid", "test"),
) -> pd.DataFrame:
    """对 train/valid/test 分别计算日度 IC、Rank IC 及汇总指标。

    ``model.predict(dataset, segment=...)`` 与 ``dataset.prepare(..., data_key=DK_R)``
    与 Qlib ``SignalRecord`` / ``SigAnaRecord`` 中 pred vs 原始 label 的设定一致。
    """
    rows: list[dict[str, Any]] = []
    for seg in segments:
        if seg not in getattr(dataset, "segments", {}):
            continue
        pred = model.predict(dataset, segment=seg)
        if pred is None or (hasattr(pred, "empty") and pred.empty):
            continue
        lab_df = dataset.prepare(seg, col_set="label", data_key=DataHandlerLP.DK_R)
        if lab_df is None or lab_df.empty:
            continue
        label = lab_df.iloc[:, 0]
        common = pred.index.intersection(label.index)
        if len(common) < 2:
            continue
        pred_a = pred.loc[common]
        label_a = label.loc[common]
        ic, ric = calc_ic(pred_a, label_a, dropna=True)
        ic_stats = summarize_ic_like_series(ic)
        ric_stats = summarize_ic_like_series(ric)
        row: dict[str, Any] = {"segment": seg, "n_pred_dates": len(ic.dropna())}
        if ic_stats:
            row.update({f"ic_{k}": v for k, v in ic_stats.items()})
        if ric_stats:
            row.update({f"rank_ic_{k}": v for k, v in ric_stats.items()})
        rows.append(row)
    return pd.DataFrame(rows)


def write_segment_ic_csv(
    model: Any,
    dataset: DatasetH,
    path: Path,
    *,
    segments: tuple[str, ...] = ("train", "valid", "test"),
) -> Path | None:
    """写入 ``segment_ic_stats.csv``；无有效数据时返回 None。"""
    df = compute_segment_ic_metrics(model, dataset, segments=segments)
    if df.empty:
        return None
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
