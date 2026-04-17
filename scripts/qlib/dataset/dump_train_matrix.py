"""训练前将 ``DatasetH`` 的 train 段特征/标签导出为 CSV，便于人工核对。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from qlib.data.dataset.handler import DataHandlerLP

from scripts.qlib.runtime.constants import normalize_writable_path


def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [
            "|".join(str(x) for x in col) if isinstance(col, tuple) else str(col)
            for col in out.columns
        ]
    return out


def _prepare_feature_df(dataset: Any, data_key: str) -> pd.DataFrame:
    return dataset.prepare("train", col_set="feature", data_key=data_key)


def dump_train_segment_csv(
    dataset: Any,
    output_dir: Path | str,
    *,
    subdir: str = "train_matrix_preview",
) -> tuple[Path, Path]:
    """导出 train 段 ``feature`` / ``label`` 为两个 CSV（宽表，索引展开为列）。

    优先 ``DK_L``；特征若失败则回退 ``DK_I``（与 importance 逻辑一致）。
    """
    root = normalize_writable_path(output_dir)
    target_dir = root / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    feat_path = target_dir / "train_feature.csv"
    label_path = target_dir / "train_label.csv"

    try:
        df_feat = _prepare_feature_df(dataset, DataHandlerLP.DK_L)
    except Exception:  # noqa: BLE001
        df_feat = _prepare_feature_df(dataset, DataHandlerLP.DK_I)

    df_label = dataset.prepare("train", col_set="label", data_key=DataHandlerLP.DK_L)

    _flatten_columns(df_feat).reset_index().to_csv(feat_path, index=False)
    _flatten_columns(df_label).reset_index().to_csv(label_path, index=False)

    return feat_path, label_path
