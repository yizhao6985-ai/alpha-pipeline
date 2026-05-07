"""在 ``DatasetH.prepare`` 之后对 **指定特征列块** 做 sklearn PCA，再交给 LightGBM。

PCA 仅在 **train** 段特征上 ``fit``，再 ``transform`` train/valid/test，避免泄露。
替换规则：去掉块内原始列，追加 ``PCA_{tag}_1`` … ``PCA_{tag}_k``。

继承 :class:`qlib.data.dataset.DatasetH` 以便 ``SignalRecord`` 等处的 ``isinstance(..., DatasetH)`` 成立。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np
import pandas as pd
from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP
from sklearn.decomposition import PCA


class GroupPCADatasetWrapper(DatasetH):
    """对 ``inner`` 的 prepare 结果做列块 PCA；``handler`` / ``segments`` 与 ``inner`` 共享。"""

    def __init__(
        self,
        inner: DatasetH,
        cols: list[str],
        *,
        tag: str,
        n_components: int | None = None,
        random_state: int = 42,
    ) -> None:
        fk = getattr(inner, "fetch_kwargs", None) or {}
        DatasetH.__init__(
            self,
            handler=inner.handler,
            segments=deepcopy(inner.segments),
            fetch_kwargs=deepcopy(fk) if fk else {},
        )
        self._inner = inner
        self._tag = tag
        self._cols = [c for c in cols if c]
        self._random_state = random_state
        self._n_components_req = n_components
        self._pca: PCA | None = None
        self._cols_fit: list[str] = []
        self._out_names: list[str] = []
        self._fit_pca()

    def _fit_pca(self) -> None:
        df = self._inner.prepare(
            "train",
            col_set=["feature", "label"],
            data_key=DataHandlerLP.DK_L,
        )
        feat = df["feature"]
        present = [c for c in self._cols if c in feat.columns]
        if len(present) < 2:
            raise ValueError(
                f"PCA 至少需要 2 列在 train 中存在，当前块 {self._tag!r} 仅匹配 {present!r}"
            )
        X = feat[present].to_numpy(dtype=np.float64)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        n_feat = len(present)
        k_req = self._n_components_req
        if k_req is None:
            k = min(3, n_feat)
        else:
            k = min(int(k_req), n_feat)
        k = max(1, k)
        self._pca = PCA(n_components=k, random_state=self._random_state)
        self._pca.fit(X)
        self._cols_fit = present
        self._out_names = [f"PCA_{self._tag}_{i + 1}" for i in range(k)]

    def _apply_feature_block(self, feat: pd.DataFrame) -> pd.DataFrame:
        if self._pca is None or not self._cols_fit:
            return feat
        missing = [c for c in self._cols_fit if c not in feat.columns]
        if missing:
            raise ValueError(f"PCA 块列在 prepare 结果中缺失: {missing}")
        X = feat[self._cols_fit].to_numpy(dtype=np.float64)
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        Z = self._pca.transform(X)
        zdf = pd.DataFrame(Z, index=feat.index, columns=self._out_names)
        rest = feat.drop(columns=self._cols_fit)
        return pd.concat([rest, zdf], axis=1)

    def prepare(
        self,
        segments: Any,
        col_set: Any = "feature",
        data_key: str = DataHandlerLP.DK_I,
        **kwargs: Any,
    ) -> Any:
        raw = self._inner.prepare(segments, col_set=col_set, data_key=data_key, **kwargs)

        if isinstance(col_set, str) and col_set == "label":
            return raw

        if _is_label_only(col_set):
            return raw

        if isinstance(raw, list):
            return [self._patch_block(x, col_set) for x in raw]

        return self._patch_block(raw, col_set)

    def _patch_block(self, raw: Any, col_set: Any) -> Any:
        if not isinstance(raw, pd.DataFrame):
            return raw

        if _is_feature_label_joint(col_set):
            out = raw.copy()
            out["feature"] = self._apply_feature_block(raw["feature"])
            return out

        if col_set == "feature":
            return self._apply_feature_block(raw)

        return raw


def _is_feature_label_joint(col_set: Any) -> bool:
    if col_set is None:
        return False
    if isinstance(col_set, (list, tuple)) and len(col_set) == 2:
        return set(col_set) == {"feature", "label"}
    return False


def _is_label_only(col_set: Any) -> bool:
    return col_set == "label"
