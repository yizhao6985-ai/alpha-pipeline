"""由 Handler 构造 ``DatasetH`` 分段。"""
from __future__ import annotations

from qlib.data.dataset import DatasetH
from qlib.data.dataset.handler import DataHandlerLP


def build_dataset(
    handler: DataHandlerLP,
    *,
    train: tuple[str, str],
    valid: tuple[str, str],
    test: tuple[str, str],
) -> DatasetH:
    return DatasetH(
        handler=handler,
        segments={"train": train, "valid": valid, "test": test},
    )
