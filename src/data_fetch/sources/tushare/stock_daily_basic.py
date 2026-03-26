from __future__ import annotations

from .client import build_tushare_clients

STOCK_DAILY_BASIC_FIELD_NAMES = [
    "ts_code",
    "trade_date",
    "close",
    "turnover_rate",
    "turnover_rate_f",
    "volume_ratio",
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "dv_ratio",
    "dv_ttm",
    "total_share",
    "float_share",
    "free_share",
    "total_mv",
    "circ_mv",
]
STOCK_DAILY_BASIC_FIELDS = ",".join(STOCK_DAILY_BASIC_FIELD_NAMES)


def fetch_stock_daily_basic(
    *,
    ts_code: str,
    start_date: str,
    end_date: str,
):
    _, pro = build_tushare_clients()
    return pro.daily_basic(
        ts_code=ts_code,
        start_date=start_date,
        end_date=end_date,
        fields=STOCK_DAILY_BASIC_FIELDS,
    )
