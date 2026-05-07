"""训练标签预设（``--label-preset`` 在 ``finalize_backtest_cli_args`` 中覆盖 ``--label-expr``）。"""
from __future__ import annotations

from scripts.qlib.handler.label import DEFAULT_LABEL_EXPR

# 名称 -> Qlib 表达式。多日收益与默认收盘 TopK「一日持有」不完全一致，回测解读须谨慎。
LABEL_PRESETS: dict[str, str] = {
    "t1": DEFAULT_LABEL_EXPR,
    "t5": "Ref($close, -5) / $close - 1",
    "t20": "Ref($close, -20) / $close - 1",
}
