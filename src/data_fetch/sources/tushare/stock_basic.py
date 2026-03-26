from __future__ import annotations

from .client import build_tushare_clients

MAIN_BOARD_MARKET = "主板"
STOCK_BASIC_FIELD_NAMES = [
    "ts_code",
    "symbol",
    "name",
    "area",
    "industry",
    "fullname",
    "enname",
    "cnspell",
    "market",
    "exchange",
    "curr_type",
    "list_status",
    "list_date",
    "delist_date",
    "act_name",
    "act_ent_type",
]
STOCK_BASIC_FIELDS = ",".join(STOCK_BASIC_FIELD_NAMES)

def _fetch_stock_list(exchange: str):
    _, pro = build_tushare_clients()
    return pro.query(
        "stock_basic",
        exchange=exchange,
        list_status="L",
        market=MAIN_BOARD_MARKET,
        fields=STOCK_BASIC_FIELDS,
    )


def fetch_sh_stock_list():
    return _fetch_stock_list("SSE")


def fetch_sz_stock_list():
    return _fetch_stock_list("SZSE")
