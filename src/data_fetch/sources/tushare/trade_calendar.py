from __future__ import annotations

import pandas as pd

from .client import build_tushare_clients

TRADE_CALENDAR_EXCHANGES = ("SSE", "SZSE")
TRADE_CALENDAR_FIELD_NAMES = [
    "exchange",
    "cal_date",
    "is_open",
    "pretrade_date",
]
TRADE_CALENDAR_FIELDS = ",".join(TRADE_CALENDAR_FIELD_NAMES)


def _fetch_trade_calendar(exchange: str, start_date: str, end_date: str):
    _, pro = build_tushare_clients()
    return pro.trade_cal(
        exchange=exchange,
        start_date=start_date,
        end_date=end_date,
        fields=TRADE_CALENDAR_FIELDS,
    )


def fetch_trade_calendar(start_date: str, end_date: str):
    frames = [
        _fetch_trade_calendar(exchange=exchange, start_date=start_date, end_date=end_date)
        for exchange in TRADE_CALENDAR_EXCHANGES
    ]
    return pd.concat(frames, ignore_index=True)
