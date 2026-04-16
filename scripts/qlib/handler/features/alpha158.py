"""
Alpha158：**不裁剪** Qlib ``Alpha158DL`` 可生成的因子块与 rolling 算子。

- ``kbar``：9 根 K 线几何因子（``kbar`` 键存在即用默认 9 条）
- ``price``：OPEN/HIGH/LOW/CLOSE/VWAP × 滞后 0–5（相对当日收盘归一）
- ``volume``：成交量滞后 0–5（相对当日量归一）
- ``rolling``：窗口 5/10/20/30/60；**不设 ``include``**（等价 ``include is None``）时，
  ``Alpha158DL.get_feature_config`` 会启用源码中 **全部** rolling 族（ROC/MA/STD/…）；
  ``exclude`` 为空列表，不排除任何一类。

说明：这与 Qlib 自带 ``Alpha158`` Handler 的默认 conf（仅部分 price、无 volume）不同；
本仓库刻意使用 **Alpha158 全量展开**。

数据侧 ``$vwap`` 与 ``$vwap_approx`` 由 ``scripts.build_qlib.to_qlib`` 写入；筹码等见 RAW handler。
"""
from __future__ import annotations

from typing import Any

from qlib.contrib.data.loader import Alpha158DL


def alpha158_classic_feature_config() -> tuple[list[str], list[str]]:
    """返回 Alpha158 **全量** ``(fields, names)``；不对 rolling 做 include 子集选择。"""
    config: dict[str, Any] = {
        "kbar": {},
        "price": {
            "windows": [0, 1, 2, 3, 4, 5],
            "feature": ["OPEN", "HIGH", "LOW", "CLOSE", "VWAP"],
        },
        "volume": {
            "windows": [0, 1, 2, 3, 4, 5],
        },
        "rolling": {
            "windows": [5, 10, 20, 30, 60],
            "exclude": [],
        },
    }
    return Alpha158DL.get_feature_config(config=config)
