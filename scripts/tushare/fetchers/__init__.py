"""
数据获取模块

提供从 Tushare 获取各类市场数据的函数
"""

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty, ensure_dir
from .stock import fetch_stock_list, fetch_stock_st
from .company import fetch_company_basic_info, fetch_financial_statements
from .index import fetch_index_basic, fetch_index_weight, fetch_index_daily
from .market import fetch_trade_calendar
from .quote import fetch_qfq_daily, fetch_daily_basic, fetch_cyq_perf

__all__ = [
    # base
    "get_tushare_pro",
    "save_csv",
    "file_exists_and_not_empty",
    "ensure_dir",
    # stock
    "fetch_stock_list",
    "fetch_stock_st",
    # company
    "fetch_company_basic_info",
    "fetch_financial_statements",
    # index
    "fetch_index_basic",
    "fetch_index_weight",
    "fetch_index_daily",
    # market
    "fetch_trade_calendar",
    # quote
    "fetch_qfq_daily",
    "fetch_daily_basic",
    "fetch_cyq_perf",
]
