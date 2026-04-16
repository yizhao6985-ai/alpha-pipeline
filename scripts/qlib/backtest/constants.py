"""模拟交易所/撮合默认值（与 ``handler.label.DEFAULT_LABEL_EXPR`` 一致时须同步）。"""
from __future__ import annotations

# T+1 收盘 / T 收盘 标签下：买卖均按收盘价撮合
EXCHANGE_DEAL_PRICE: tuple[str, str] = ("$close", "$close")
