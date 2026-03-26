from __future__ import annotations

from .client import build_tushare_clients

STOCK_ST_FIELD_NAMES = [
    "ts_code",
    "name",
    "trade_date",
    "type",
    "type_name",
]
STOCK_ST_FIELDS = ",".join(STOCK_ST_FIELD_NAMES)


def fetch_stock_st_list(trade_date: str):
    _, pro = build_tushare_clients()
    return pro.stock_st(
        trade_date=trade_date,
        fields=STOCK_ST_FIELDS,
    )
