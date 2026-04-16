"""DatasetH：工厂方法与从 CLI 参数构建。"""
from __future__ import annotations

from scripts.qlib.dataset.factory import build_dataset
from scripts.qlib.dataset.from_args import build_training_dataset

__all__ = [
    "build_dataset",
    "build_training_dataset",
]
