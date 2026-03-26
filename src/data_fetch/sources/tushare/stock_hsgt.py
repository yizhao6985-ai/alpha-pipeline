from __future__ import annotations

import pandas as pd

from .client import build_tushare_clients

STOCK_HSGT_FIELD_NAMES = [
    "ts_code",
    "trade_date",
    "type",
    "name",
    "type_name",
]
STOCK_HSGT_FIELDS = ",".join(STOCK_HSGT_FIELD_NAMES)
STOCK_HSGT_TYPES = ("HK_SZ", "HK_SH")


def _fetch_stock_hsgt(type_: str, start_date: str, end_date: str):
    _, pro = build_tushare_clients()
    return pro.stock_hsgt(
        type=type_,
        start_date=start_date,
        end_date=end_date,
        fields=STOCK_HSGT_FIELDS,
    )


def fetch_stock_hsgt_list(start_date: str, end_date: str):
    frames = [
        _fetch_stock_hsgt(type_=type_, start_date=start_date, end_date=end_date)
        for type_ in STOCK_HSGT_TYPES
    ]
    return pd.concat(frames, ignore_index=True)
