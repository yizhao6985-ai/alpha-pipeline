from __future__ import annotations

from .client import build_tushare_clients

STOCK_QFQ_5MIN_FIELD_NAMES = [
    "ts_code",
    "trade_time",
    "open",
    "close",
    "high",
    "low",
    "vol",
    "amount",
]


def fetch_stock_qfq_5min(
    *,
    ts_code: str,
    start_date: str,
    end_date: str,
):
    ts, _ = build_tushare_clients()
    mins_df = ts.pro_bar(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        asset="E",
        adj="qfq",
        freq="5MIN",
    )
    if mins_df is None:
        return mins_df
    available_columns = [column for column in STOCK_QFQ_5MIN_FIELD_NAMES if column in mins_df.columns]
    return mins_df[available_columns]
