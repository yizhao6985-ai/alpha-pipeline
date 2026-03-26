from __future__ import annotations

from .client import build_tushare_clients, call_with_retry

STOCK_ADJ_FACTOR_FIELD_NAMES = [
    "ts_code",
    "trade_date",
    "adj_factor",
]
STOCK_ADJ_FACTOR_FIELDS = ",".join(STOCK_ADJ_FACTOR_FIELD_NAMES)


def fetch_stock_adj_factor(
    *,
    ts_code: str,
    start_date: str,
    end_date: str,
):
    _, pro = build_tushare_clients()
    return call_with_retry(
        lambda: pro.adj_factor(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=STOCK_ADJ_FACTOR_FIELDS,
        )
    )
