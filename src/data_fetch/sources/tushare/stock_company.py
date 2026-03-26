from __future__ import annotations

from .client import build_tushare_clients

STOCK_COMPANY_FIELD_NAMES = [
    "ts_code",
    "com_name",
    "com_id",
    "exchange",
    "chairman",
    "manager",
    "secretary",
    "reg_capital",
    "setup_date",
    "province",
    "city",
    "introduction",
    "website",
    "email",
    "office",
    "employees",
    "main_business",
    "business_scope",
]
STOCK_COMPANY_FIELDS = ",".join(STOCK_COMPANY_FIELD_NAMES)


def _fetch_stock_company(exchange: str):
    _, pro = build_tushare_clients()
    return pro.stock_company(exchange=exchange, fields=STOCK_COMPANY_FIELDS)


def fetch_sh_stock_company():
    return _fetch_stock_company("SSE")


def fetch_sz_stock_company():
    return _fetch_stock_company("SZSE")
