"""训练标签表达式（与收盘撮合价一致）。"""
from __future__ import annotations

# T 日特征、标签为 T+1 收盘相对 T 日收盘；回测须 deal_price=("$close","$close") 才与标签一致
DEFAULT_LABEL_EXPR = "Ref($close, -1) / $close - 1"
