from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .datasets import (
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
)

GLOBAL_MIDDLEWARE = "*"
GLOBAL_SOURCE = "*"
MiddlewareKey = str | tuple[str, str]


@dataclass(slots=True)
class FetchContext:
    source_name: str
    dataset: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class FetchResult:
    data: Any


Middleware = Callable[[FetchResult, FetchContext], FetchResult]


class DataSource(Protocol):
    source_name: str

    def fetch(self, dataset: str, **params: Any) -> FetchResult:
        """Fetch raw data for a dataset."""
        ...

class DataFetcher:
    def __init__(
        self,
        provider: DataSource,
        middlewares: dict[MiddlewareKey, list[Middleware]] | None = None,
    ) -> None:
        self.provider = provider
        self.middlewares = {name: list(chain) for name, chain in (middlewares or {}).items()}

    def register_middleware(
        self,
        dataset: str,
        middleware: Middleware,
        source_name: str = GLOBAL_SOURCE,
    ) -> None:
        key: MiddlewareKey = dataset if source_name == GLOBAL_SOURCE else (source_name, dataset)
        self.middlewares.setdefault(key, []).append(middleware)

    def fetch(self, dataset: str, **params: Any) -> FetchResult:
        source_name = self.provider.source_name
        context = FetchContext(source_name=source_name, dataset=dataset, params=dict(params))
        result = self.provider.fetch(dataset, **params)
        middleware_chain = (
            self.middlewares.get(GLOBAL_MIDDLEWARE, [])
            + self.middlewares.get((source_name, GLOBAL_MIDDLEWARE), [])
            + self.middlewares.get(dataset, [])
            + self.middlewares.get((source_name, dataset), [])
        )
        for middleware in middleware_chain:
            result = middleware(result, context)
        return result

    def fetch_stock_list(self, update_date: str) -> FetchResult:
        sh_result = self.fetch(STOCK_LIST, update_date=update_date, exchange="SSE")
        sz_result = self.fetch(STOCK_LIST, update_date=update_date, exchange="SZSE")
        return FetchResult(
            data={
                "sh": sh_result.data,
                "sz": sz_result.data,
            }
        )

    def fetch_company_basic_info(self, update_date: str) -> FetchResult:
        sh_result = self.fetch(COMPANY_BASIC_INFO, update_date=update_date, exchange="SSE")
        sz_result = self.fetch(COMPANY_BASIC_INFO, update_date=update_date, exchange="SZSE")
        return FetchResult(
            data={
                "sh": sh_result.data,
                "sz": sz_result.data,
            }
        )

    def fetch_company_income(
        self,
        *,
        ts_code: str,
        ann_date: str | None = None,
        f_ann_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str | None = None,
        report_type: str | None = None,
        comp_type: str | None = None,
        fields: str | None = None,
    ) -> FetchResult:
        return self.fetch(
            COMPANY_INCOME,
            ts_code=ts_code,
            ann_date=ann_date,
            f_ann_date=f_ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
            fields=fields,
        )

    def fetch_company_balancesheet(
        self,
        *,
        ts_code: str,
        ann_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str | None = None,
        report_type: str | None = None,
        comp_type: str | None = None,
        fields: str | None = None,
    ) -> FetchResult:
        return self.fetch(
            COMPANY_BALANCESHEET,
            ts_code=ts_code,
            ann_date=ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
            fields=fields,
        )

    def fetch_company_cashflow(
        self,
        *,
        ts_code: str,
        ann_date: str | None = None,
        f_ann_date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str | None = None,
        report_type: str | None = None,
        comp_type: str | None = None,
        is_calc: int | None = None,
        fields: str | None = None,
    ) -> FetchResult:
        return self.fetch(
            COMPANY_CASHFLOW,
            ts_code=ts_code,
            ann_date=ann_date,
            f_ann_date=f_ann_date,
            start_date=start_date,
            end_date=end_date,
            period=period,
            report_type=report_type,
            comp_type=comp_type,
            is_calc=is_calc,
            fields=fields,
        )

    def fetch_trade_calendar(self, update_date: str) -> FetchResult:
        return self.fetch(MARKET_TRADE_CALENDAR, update_date=update_date)

    def fetch_market_index_basic(self) -> FetchResult:
        return self.fetch(MARKET_INDEX_BASIC)

    def fetch_market_index_weight(
        self,
        *,
        index_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> FetchResult:
        return self.fetch(
            MARKET_INDEX_WEIGHT,
            index_code=index_code,
            start_date=start_date,
            end_date=end_date,
        )

    def fetch_stock_hsgt_list(self, update_date: str) -> FetchResult:
        return self.fetch(STOCK_HSGT_LIST, update_date=update_date)

    def fetch_st_stock_list(self, update_date: str) -> FetchResult:
        return self.fetch(STOCK_ST_LIST, update_date=update_date)

    def fetch_stock_qfq_daily(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        return self.fetch(
            STOCK_QFQ_DAILY,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def fetch_stock_qfq_5min(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        return self.fetch(
            STOCK_QFQ_5MIN,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )

    def fetch_stock_daily_basic(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> FetchResult:
        return self.fetch(
            STOCK_DAILY_BASIC,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )


def build_default_fetcher() -> DataFetcher:
    from .middlewares import build_default_middlewares
    from .providers import TushareDataSource

    return DataFetcher(
        provider=TushareDataSource(),
        middlewares=build_default_middlewares(),
    )
