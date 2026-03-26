from __future__ import annotations

from .client import build_tushare_clients

STOCK_QFQ_DAILY_FIELD_NAMES = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
]


def fetch_stock_qfq_daily(
    *,
    ts_code: str,
    start_date: str,
    end_date: str,
):
    ts, _ = build_tushare_clients()
    daily_df = ts.pro_bar(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        asset="E",
        adj="qfq",
        freq="D",
    )
    if daily_df is None:
        return daily_df
    available_columns = [column for column in STOCK_QFQ_DAILY_FIELD_NAMES if column in daily_df.columns]
    return daily_df[available_columns]
