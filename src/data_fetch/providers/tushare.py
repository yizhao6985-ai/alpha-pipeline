from __future__ import annotations

from typing import Any

from ..config import get_default_fetch_start_date
from ..datasets import (
    COMPANY_BASIC_INFO,
    COMPANY_BALANCESHEET,
    COMPANY_CASHFLOW,
    COMPANY_INCOME,
    MARKET_INDEX_BASIC,
    MARKET_INDEX_WEIGHT,
    MARKET_TRADE_CALENDAR,
    STOCK_HSGT_LIST,
    STOCK_DAILY_BASIC,
    STOCK_LIST,
    STOCK_QFQ_5MIN,
    STOCK_QFQ_DAILY,
    STOCK_ST_LIST,
    TUSHARE_SOURCE,
)
from ..fetcher import FetchResult
from ..sources.tushare import (
    fetch_balance_sheet_statement,
    fetch_cash_flow_statement,
    fetch_index_basic,
    fetch_index_weight,
    fetch_income_statement,
    fetch_sh_stock_company,
    fetch_sh_stock_list,
    fetch_stock_hsgt_list,
    fetch_stock_daily_basic,
    fetch_stock_qfq_5min,
    fetch_stock_qfq_daily,
    fetch_stock_st_list,
)
from ..sources.tushare import fetch_sz_stock_company, fetch_sz_stock_list
from ..sources.tushare.trade_calendar import fetch_trade_calendar


class TushareDataSource:
    source_name = TUSHARE_SOURCE

    def fetch(self, dataset: str, **params: Any) -> FetchResult:
        if dataset == COMPANY_BASIC_INFO:
            exchange = params["exchange"]
            if exchange == "SSE":
                return FetchResult(data=fetch_sh_stock_company())
            if exchange == "SZSE":
                return FetchResult(data=fetch_sz_stock_company())
            raise ValueError(f"Unsupported company basic info exchange: {exchange}")

        if dataset == COMPANY_BALANCESHEET:
            return FetchResult(
                data=fetch_balance_sheet_statement(
                    ts_code=params["ts_code"],
                    ann_date=params.get("ann_date"),
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date"),
                    period=params.get("period"),
                    report_type=params.get("report_type"),
                    comp_type=params.get("comp_type"),
                    fields=params.get("fields"),
                )
            )

        if dataset == COMPANY_CASHFLOW:
            return FetchResult(
                data=fetch_cash_flow_statement(
                    ts_code=params["ts_code"],
                    ann_date=params.get("ann_date"),
                    f_ann_date=params.get("f_ann_date"),
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date"),
                    period=params.get("period"),
                    report_type=params.get("report_type"),
                    comp_type=params.get("comp_type"),
                    is_calc=params.get("is_calc"),
                    fields=params.get("fields"),
                )
            )

        if dataset == COMPANY_INCOME:
            return FetchResult(
                data=fetch_income_statement(
                    ts_code=params["ts_code"],
                    ann_date=params.get("ann_date"),
                    f_ann_date=params.get("f_ann_date"),
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date"),
                    period=params.get("period"),
                    report_type=params.get("report_type"),
                    comp_type=params.get("comp_type"),
                    fields=params.get("fields"),
                )
            )

        if dataset == MARKET_INDEX_BASIC:
            return FetchResult(data=fetch_index_basic())

        if dataset == MARKET_INDEX_WEIGHT:
            return FetchResult(
                data=fetch_index_weight(
                    index_code=params["index_code"],
                    start_date=params.get("start_date"),
                    end_date=params.get("end_date"),
                )
            )

        if dataset == MARKET_TRADE_CALENDAR:
            return FetchResult(
                data=fetch_trade_calendar(
                    start_date=get_default_fetch_start_date(),
                    end_date=params["update_date"],
                )
            )

        if dataset == STOCK_HSGT_LIST:
            return FetchResult(
                data=fetch_stock_hsgt_list(
                    start_date=get_default_fetch_start_date(),
                    end_date=params["update_date"],
                )
            )

        if dataset == STOCK_LIST:
            exchange = params["exchange"]
            if exchange == "SSE":
                return FetchResult(data=fetch_sh_stock_list())
            if exchange == "SZSE":
                return FetchResult(data=fetch_sz_stock_list())
            raise ValueError(f"Unsupported stock list exchange: {exchange}")

        if dataset == STOCK_ST_LIST:
            return FetchResult(data=fetch_stock_st_list(trade_date=params["update_date"]))

        if dataset == STOCK_QFQ_DAILY:
            return FetchResult(
                data=fetch_stock_qfq_daily(
                    ts_code=params["ts_code"],
                    start_date=params["start_date"],
                    end_date=params["end_date"],
                )
            )

        if dataset == STOCK_QFQ_5MIN:
            return FetchResult(
                data=fetch_stock_qfq_5min(
                    ts_code=params["ts_code"],
                    start_date=params["start_date"],
                    end_date=params["end_date"],
                )
            )

        if dataset == STOCK_DAILY_BASIC:
            return FetchResult(
                data=fetch_stock_daily_basic(
                    ts_code=params["ts_code"],
                    start_date=params["start_date"],
                    end_date=params["end_date"],
                )
            )

        raise ValueError(f"Unsupported dataset: {dataset}")
