from __future__ import annotations

from .client import build_tushare_clients

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
        adjfactor=True,
    )
    return daily_df
