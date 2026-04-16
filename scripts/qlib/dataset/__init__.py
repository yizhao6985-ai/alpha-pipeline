"""Dataset 工厂：由 handler 与时间分段构造 ``qlib.data.dataset.DatasetH``。"""

from scripts.qlib.dataset.factory import build_dataset
from scripts.qlib.dataset.from_args import build_training_dataset

__all__ = [
    "build_dataset",
    "build_training_dataset",
]
