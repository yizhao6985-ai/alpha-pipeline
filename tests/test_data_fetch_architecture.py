import json
from datetime import datetime

import pandas as pd
import pytest

from data_fetch.datasets import (
    COMPANY_BASIC_INFO,
    COMPANY_BALANCESHEET,
    COMPANY_CASHFLOW,
    COMPANY_INCOME,
    MARKET_INDEX_BASIC,
    MARKET_INDEX_WEIGHT,
    MARKET_TRADE_CALENDAR,
    STOCK_HSGT_LIST,
    STOCK_LIST,
    STOCK_DAILY_BASIC,
    STOCK_QFQ_5MIN,
    STOCK_QFQ_DAILY,
    STOCK_ST_LIST,
    TUSHARE_SOURCE,
)
from data_fetch import cli
from data_fetch.config import get_default_fetch_start_date
from data_fetch.runtime import (
    DEFAULT_INDEX_CODES,
    DEFAULT_TS_CODES,
    build_runtime_targets_payload,
    get_default_index_basic_markets,
    get_default_index_codes,
    get_default_stock_index_basic_categories,
    get_default_ts_codes,
    get_runtime_ts_codes,
    write_runtime_targets,
)
from data_fetch.fetcher import (
    GLOBAL_MIDDLEWARE,
    DataFetcher,
    FetchResult,
    build_default_fetcher,
)
from data_fetch.middlewares import build_default_middlewares
from data_fetch.path_manager import (
    build_quote_daily_basic_path,
    build_quote_qfq_5min_path,
    build_quote_qfq_daily_path,
    build_company_basic_info_path,
    build_financial_statement_path,
    build_index_basic_path,
    build_index_basic_source_dir,
    build_index_weight_path,
    build_stock_list_path,
    build_stock_st_list_path,
    build_trade_calendar_path,
    has_current_data,
    has_current_index_basic_data,
)
from data_fetch.sources.tushare.index_basic import filter_stock_index_basic
from data_fetch.sources.tushare.stock_basic import _fetch_stock_list


class FakeProvider:
    def __init__(self, results: dict[str, FetchResult], source_name: str = "fake"):
        self.results = results
        self.source_name = source_name
        self.calls: list[tuple[str, dict[str, object]]] = []

    def fetch(self, dataset: str, **params: object) -> FetchResult:
        self.calls.append((dataset, params))
        return self.results[dataset]


def test_data_fetcher_applies_middlewares_in_order():
    provider = FakeProvider(
        {
            STOCK_LIST: FetchResult(
                data=["raw"],
            )
        }
    )

    def add_global(result, context):
        return FetchResult(
            data=result.data + [context.dataset],
        )

    def add_dataset(result, context):
        return FetchResult(
            data=result.data + [context.params["query_date"]],
        )

    fetcher = DataFetcher(
        provider=provider,
        middlewares={
            GLOBAL_MIDDLEWARE: [add_global],
            STOCK_LIST: [add_dataset],
        },
    )

    result = fetcher.fetch(STOCK_LIST, query_date="20260320")

    assert provider.calls == [(STOCK_LIST, {"query_date": "20260320"})]
    assert result.data == ["raw", STOCK_LIST, "20260320"]


def test_data_fetcher_supports_source_specific_middlewares():
    provider = FakeProvider(
        {
            STOCK_LIST: FetchResult(
                data=[],
            )
        },
        source_name="demo",
    )

    def add_source(result, context):
        return FetchResult(
            data=result.data + [context.source_name],
        )

    def add_source_dataset(result, context):
        return FetchResult(
            data=result.data + [context.dataset],
        )

    fetcher = DataFetcher(
        provider=provider,
        middlewares={
            ("demo", GLOBAL_MIDDLEWARE): [add_source],
            ("demo", STOCK_LIST): [add_source_dataset],
        },
    )

    result = fetcher.fetch(STOCK_LIST, query_date="20260320")

    assert result.data == ["demo", STOCK_LIST]


def test_default_middlewares_do_not_change_spot():
    raw_df = pd.DataFrame({"symbol": ["600000"]})
    provider = FakeProvider(
        {
            STOCK_LIST: FetchResult(
                data=raw_df,
            )
        },
        source_name=TUSHARE_SOURCE,
    )
    fetcher = DataFetcher(provider=provider, middlewares=build_default_middlewares())

    result = fetcher.fetch(STOCK_LIST, update_date="20260320")

    assert result.data.equals(raw_df)


def test_fetch_stock_list_combines_sh_and_sz_results():
    sh_df = pd.DataFrame(
        {
            "symbol": ["600000"],
        }
    )
    sz_df = pd.DataFrame(
        {
            "symbol": ["000001"],
        }
    )

    class StockListProvider:
        source_name = "fake"

        def __init__(self):
            self.calls = []

        def fetch(self, dataset: str, **params: object) -> FetchResult:
            self.calls.append((dataset, params))
            if params["exchange"] == "SSE":
                return FetchResult(data=sh_df)
            if params["exchange"] == "SZSE":
                return FetchResult(data=sz_df)
            raise AssertionError(f"unexpected exchange: {params['exchange']}")

    provider = StockListProvider()
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_stock_list(update_date="20260320")

    assert provider.calls == [
        (STOCK_LIST, {"update_date": "20260320", "exchange": "SSE"}),
        (STOCK_LIST, {"update_date": "20260320", "exchange": "SZSE"}),
    ]
    assert result.data == {
        "sh": sh_df,
        "sz": sz_df,
    }


def test_fetch_company_basic_info_combines_sh_and_sz_results():
    sh_df = pd.DataFrame({"ts_code": ["600000.SH"]})
    sz_df = pd.DataFrame({"ts_code": ["000001.SZ"]})

    class CompanyBasicInfoProvider:
        source_name = "fake"

        def __init__(self):
            self.calls = []

        def fetch(self, dataset: str, **params: object) -> FetchResult:
            self.calls.append((dataset, params))
            if params["exchange"] == "SSE":
                return FetchResult(data=sh_df)
            if params["exchange"] == "SZSE":
                return FetchResult(data=sz_df)
            raise AssertionError(f"unexpected exchange: {params['exchange']}")

    provider = CompanyBasicInfoProvider()
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_company_basic_info(update_date="20260320")

    assert provider.calls == [
        (COMPANY_BASIC_INFO, {"update_date": "20260320", "exchange": "SSE"}),
        (COMPANY_BASIC_INFO, {"update_date": "20260320", "exchange": "SZSE"}),
    ]
    assert result.data == {
        "sh": sh_df,
        "sz": sz_df,
    }


def test_fetch_company_income_passes_query_params():
    income_df = pd.DataFrame({"ts_code": ["600000.SH"], "end_date": ["20241231"]})
    provider = FakeProvider(
        {
            COMPANY_INCOME: FetchResult(
                data=income_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_company_income(
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        period="20241231",
        report_type="1",
        comp_type="2",
        fields="ts_code,end_date,total_revenue,n_income",
    )

    assert provider.calls == [
        (
            COMPANY_INCOME,
            {
                "ts_code": "600000.SH",
                "ann_date": None,
                "f_ann_date": None,
                "start_date": "20240101",
                "end_date": "20241231",
                "period": "20241231",
                "report_type": "1",
                "comp_type": "2",
                "fields": "ts_code,end_date,total_revenue,n_income",
            },
        ),
    ]
    assert result.data.equals(income_df)


def test_fetch_company_balancesheet_passes_query_params():
    balancesheet_df = pd.DataFrame({"ts_code": ["600000.SH"], "end_date": ["20241231"]})
    provider = FakeProvider(
        {
            COMPANY_BALANCESHEET: FetchResult(
                data=balancesheet_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_company_balancesheet(
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        period="20241231",
        report_type="1",
        comp_type="2",
        fields="ts_code,end_date,total_assets,total_liab",
    )

    assert provider.calls == [
        (
            COMPANY_BALANCESHEET,
            {
                "ts_code": "600000.SH",
                "ann_date": None,
                "start_date": "20240101",
                "end_date": "20241231",
                "period": "20241231",
                "report_type": "1",
                "comp_type": "2",
                "fields": "ts_code,end_date,total_assets,total_liab",
            },
        ),
    ]
    assert result.data.equals(balancesheet_df)


def test_fetch_company_cashflow_passes_query_params():
    cashflow_df = pd.DataFrame({"ts_code": ["600000.SH"], "end_date": ["20241231"]})
    provider = FakeProvider(
        {
            COMPANY_CASHFLOW: FetchResult(
                data=cashflow_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_company_cashflow(
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        period="20241231",
        report_type="1",
        comp_type="2",
        is_calc=1,
        fields="ts_code,end_date,n_cashflow_act,free_cashflow",
    )

    assert provider.calls == [
        (
            COMPANY_CASHFLOW,
            {
                "ts_code": "600000.SH",
                "ann_date": None,
                "f_ann_date": None,
                "start_date": "20240101",
                "end_date": "20241231",
                "period": "20241231",
                "report_type": "1",
                "comp_type": "2",
                "is_calc": 1,
                "fields": "ts_code,end_date,n_cashflow_act,free_cashflow",
            },
        ),
    ]
    assert result.data.equals(cashflow_df)


def test_fetch_st_stock_list_passes_update_date():
    st_df = pd.DataFrame({"ts_code": ["600289.SH"]})
    provider = FakeProvider(
        {
            STOCK_ST_LIST: FetchResult(
                data=st_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_st_stock_list(update_date="20260320")

    assert provider.calls == [
        (STOCK_ST_LIST, {"update_date": "20260320"}),
    ]
    assert result.data.equals(st_df)


def test_fetch_trade_calendar_passes_update_date():
    trade_calendar_df = pd.DataFrame({"cal_date": ["20260320"]})
    provider = FakeProvider(
        {
            MARKET_TRADE_CALENDAR: FetchResult(
                data=trade_calendar_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_trade_calendar(update_date="20260320")

    assert provider.calls == [
        (MARKET_TRADE_CALENDAR, {"update_date": "20260320"}),
    ]
    assert result.data.equals(trade_calendar_df)


def test_fetch_market_index_basic_without_date_params():
    index_basic_df = pd.DataFrame({"ts_code": ["000001.SH"]})
    provider = FakeProvider(
        {
            MARKET_INDEX_BASIC: FetchResult(
                data=index_basic_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_market_index_basic()

    assert provider.calls == [
        (MARKET_INDEX_BASIC, {}),
    ]
    assert result.data.equals(index_basic_df)


def test_fetch_market_index_weight_forwards_query_params():
    index_weight_df = pd.DataFrame({"index_code": ["399300.SZ"]})
    provider = FakeProvider(
        {
            MARKET_INDEX_WEIGHT: FetchResult(
                data=index_weight_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_market_index_weight(
        index_code="399300.SZ",
    )

    assert provider.calls == [
        (
            MARKET_INDEX_WEIGHT,
            {
                "index_code": "399300.SZ",
            },
        ),
    ]
    assert result.data.equals(index_weight_df)


def test_fetch_stock_hsgt_list_passes_update_date():
    hsgt_df = pd.DataFrame({"ts_code": ["000001.SZ"]})
    provider = FakeProvider(
        {
            STOCK_HSGT_LIST: FetchResult(
                data=hsgt_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_stock_hsgt_list(update_date="20260320")

    assert provider.calls == [
        (STOCK_HSGT_LIST, {"update_date": "20260320"}),
    ]
    assert result.data.equals(hsgt_df)


def test_fetch_stock_qfq_daily_passes_query_params():
    qfq_df = pd.DataFrame({"ts_code": ["000001.SZ"]})
    provider = FakeProvider(
        {
            STOCK_QFQ_DAILY: FetchResult(
                data=qfq_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_stock_qfq_daily(
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    )

    assert provider.calls == [
        (
            STOCK_QFQ_DAILY,
            {
                "ts_code": "000001.SZ",
                "start_date": "20240101",
                "end_date": "20241231",
            },
        )
    ]
    assert result.data.equals(qfq_df)


def test_fetch_stock_qfq_5min_passes_query_params():
    qfq_df = pd.DataFrame({"ts_code": ["000001.SZ"]})
    provider = FakeProvider(
        {
            STOCK_QFQ_5MIN: FetchResult(
                data=qfq_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_stock_qfq_5min(
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    )

    assert provider.calls == [
        (
            STOCK_QFQ_5MIN,
            {
                "ts_code": "000001.SZ",
                "start_date": "20240101",
                "end_date": "20241231",
            },
        )
    ]
    assert result.data.equals(qfq_df)


def test_fetch_stock_daily_basic_passes_query_params():
    daily_basic_df = pd.DataFrame({"ts_code": ["000001.SZ"]})
    provider = FakeProvider(
        {
            STOCK_DAILY_BASIC: FetchResult(
                data=daily_basic_df,
            ),
        }
    )
    fetcher = DataFetcher(provider=provider)

    result = fetcher.fetch_stock_daily_basic(
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    )

    assert provider.calls == [
        (
            STOCK_DAILY_BASIC,
            {
                "ts_code": "000001.SZ",
                "start_date": "20240101",
                "end_date": "20241231",
            },
        )
    ]
    assert result.data.equals(daily_basic_df)


def test_tushare_provider_trade_calendar_uses_default_start_date():
    expected_df = pd.DataFrame({"cal_date": ["20260320"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_trade_calendar(*, start_date, end_date):
        calls.append((start_date, end_date))
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_trade_calendar
    tushare_provider_module.fetch_trade_calendar = fake_fetch_trade_calendar
    try:
        result = provider.fetch(MARKET_TRADE_CALENDAR, update_date="20260320")
    finally:
        tushare_provider_module.fetch_trade_calendar = original

    assert calls == [("20180101", "20260320")]
    assert result.data.equals(expected_df)


def test_tushare_provider_market_index_weight_forwards_query_params():
    expected_df = pd.DataFrame({"index_code": ["399300.SZ"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_index_weight(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_index_weight
    tushare_provider_module.fetch_index_weight = fake_fetch_index_weight
    try:
        result = provider.fetch(
            MARKET_INDEX_WEIGHT,
            index_code="399300.SZ",
        )
    finally:
        tushare_provider_module.fetch_index_weight = original

    assert calls == [
        {
            "index_code": "399300.SZ",
            "start_date": None,
            "end_date": None,
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_market_index_basic_fetches_index_list():
    expected_df = pd.DataFrame({"ts_code": ["000001.SH"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_index_basic():
        calls.append("called")
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_index_basic
    tushare_provider_module.fetch_index_basic = fake_fetch_index_basic
    try:
        result = provider.fetch(MARKET_INDEX_BASIC)
    finally:
        tushare_provider_module.fetch_index_basic = original

    assert calls == ["called"]
    assert result.data.equals(expected_df)


def test_tushare_provider_stock_qfq_daily_forwards_query_params():
    expected_df = pd.DataFrame({"ts_code": ["000001.SZ"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_stock_qfq_daily(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_stock_qfq_daily
    tushare_provider_module.fetch_stock_qfq_daily = fake_fetch_stock_qfq_daily
    try:
        result = provider.fetch(
            STOCK_QFQ_DAILY,
            ts_code="000001.SZ",
            start_date="20240101",
            end_date="20241231",
        )
    finally:
        tushare_provider_module.fetch_stock_qfq_daily = original

    assert calls == [
        {
            "ts_code": "000001.SZ",
            "start_date": "20240101",
            "end_date": "20241231",
            "fields": (
                "ts_code,trade_date,close,turnover_rate,turnover_rate_f,volume_ratio,pe,pe_ttm,pb,ps,ps_ttm,"
                "dv_ratio,dv_ttm,total_share,float_share,free_share,total_mv,circ_mv"
            ),
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_stock_qfq_5min_forwards_query_params():
    expected_df = pd.DataFrame({"ts_code": ["000001.SZ"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_stock_qfq_5min(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_stock_qfq_5min
    tushare_provider_module.fetch_stock_qfq_5min = fake_fetch_stock_qfq_5min
    try:
        result = provider.fetch(
            STOCK_QFQ_5MIN,
            ts_code="000001.SZ",
            start_date="20240101",
            end_date="20241231",
        )
    finally:
        tushare_provider_module.fetch_stock_qfq_5min = original

    assert calls == [
        {
            "ts_code": "000001.SZ",
            "start_date": "20240101",
            "end_date": "20241231",
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_stock_daily_basic_forwards_query_params():
    expected_df = pd.DataFrame({"ts_code": ["000001.SZ"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_stock_daily_basic(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_stock_daily_basic
    tushare_provider_module.fetch_stock_daily_basic = fake_fetch_stock_daily_basic
    try:
        result = provider.fetch(
            STOCK_DAILY_BASIC,
            ts_code="000001.SZ",
            start_date="20240101",
            end_date="20241231",
        )
    finally:
        tushare_provider_module.fetch_stock_daily_basic = original

    assert calls == [
        {
            "ts_code": "000001.SZ",
            "start_date": "20240101",
            "end_date": "20241231",
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_income_forwards_query_params():
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_income_statement(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_income_statement
    tushare_provider_module.fetch_income_statement = fake_fetch_income_statement
    try:
        result = provider.fetch(
            COMPANY_INCOME,
            ts_code="600000.SH",
            start_date="20240101",
            end_date="20241231",
            period="20241231",
            report_type="1",
            comp_type="2",
            fields="ts_code,end_date,total_revenue",
        )
    finally:
        tushare_provider_module.fetch_income_statement = original

    assert calls == [
        {
            "ts_code": "600000.SH",
            "ann_date": None,
            "f_ann_date": None,
            "start_date": "20240101",
            "end_date": "20241231",
            "period": "20241231",
            "report_type": "1",
            "comp_type": "2",
            "fields": "ts_code,end_date,total_revenue",
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_balancesheet_forwards_query_params():
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_balance_sheet_statement(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_balance_sheet_statement
    tushare_provider_module.fetch_balance_sheet_statement = fake_fetch_balance_sheet_statement
    try:
        result = provider.fetch(
            COMPANY_BALANCESHEET,
            ts_code="600000.SH",
            start_date="20240101",
            end_date="20241231",
            period="20241231",
            report_type="1",
            comp_type="2",
            fields="ts_code,end_date,total_assets",
        )
    finally:
        tushare_provider_module.fetch_balance_sheet_statement = original

    assert calls == [
        {
            "ts_code": "600000.SH",
            "ann_date": None,
            "start_date": "20240101",
            "end_date": "20241231",
            "period": "20241231",
            "report_type": "1",
            "comp_type": "2",
            "fields": "ts_code,end_date,total_assets",
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_cashflow_forwards_query_params():
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_cash_flow_statement(**kwargs):
        calls.append(kwargs)
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_cash_flow_statement
    tushare_provider_module.fetch_cash_flow_statement = fake_fetch_cash_flow_statement
    try:
        result = provider.fetch(
            COMPANY_CASHFLOW,
            ts_code="600000.SH",
            start_date="20240101",
            end_date="20241231",
            period="20241231",
            report_type="1",
            comp_type="2",
            is_calc=1,
            fields="ts_code,end_date,n_cashflow_act",
        )
    finally:
        tushare_provider_module.fetch_cash_flow_statement = original

    assert calls == [
        {
            "ts_code": "600000.SH",
            "ann_date": None,
            "f_ann_date": None,
            "start_date": "20240101",
            "end_date": "20241231",
            "period": "20241231",
            "report_type": "1",
            "comp_type": "2",
            "is_calc": 1,
            "fields": "ts_code,end_date,n_cashflow_act",
        }
    ]
    assert result.data.equals(expected_df)


def test_tushare_provider_stock_hsgt_uses_default_date_range():
    expected_df = pd.DataFrame({"ts_code": ["000001.SZ"]})

    from data_fetch.providers.tushare import TushareDataSource

    provider = TushareDataSource()

    calls = []

    def fake_fetch_stock_hsgt_list(*, start_date, end_date):
        calls.append((start_date, end_date))
        return expected_df

    import data_fetch.providers.tushare as tushare_provider_module

    original = tushare_provider_module.fetch_stock_hsgt_list
    tushare_provider_module.fetch_stock_hsgt_list = fake_fetch_stock_hsgt_list
    try:
        result = provider.fetch(STOCK_HSGT_LIST, update_date="20260320")
    finally:
        tushare_provider_module.fetch_stock_hsgt_list = original

    assert calls == [("20180101", "20260320")]
    assert result.data.equals(expected_df)


def test_tushare_stock_list_uses_query(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def query(self, api_name, **kwargs):
            self.calls.append((api_name, kwargs))
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_basic.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    result = _fetch_stock_list("SSE")

    assert fake_pro.calls == [
        (
            "stock_basic",
            {
                "exchange": "SSE",
                "list_status": "L",
                "market": "主板",
                "fields": (
                    "ts_code,symbol,name,area,industry,fullname,enname,cnspell,"
                    "market,exchange,curr_type,list_status,list_date,delist_date,"
                    "act_name,act_ent_type"
                ),
            },
        )
    ]
    assert result.equals(expected_df)


def test_tushare_income_uses_filtered_query_params(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def income(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.income_statement.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare.income_statement import fetch_income_statement

    result = fetch_income_statement(
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        period="20241231",
        report_type="1",
        fields="ts_code,end_date,total_revenue",
    )

    assert fake_pro.calls == [
        {
            "ts_code": "600000.SH",
            "start_date": "20240101",
            "end_date": "20241231",
            "period": "20241231",
            "report_type": "1",
            "fields": "ts_code,end_date,total_revenue",
        }
    ]
    assert result.equals(expected_df)


def test_tushare_income_uses_all_fields_by_default(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def income(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.income_statement.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare.income_statement import (
        INCOME_ALL_FIELDS,
        fetch_income_statement,
    )

    result = fetch_income_statement(ts_code="600000.SH")

    assert fake_pro.calls == [{"ts_code": "600000.SH", "fields": INCOME_ALL_FIELDS}]
    assert result.equals(expected_df)


def test_tushare_balance_sheet_uses_filtered_query_params(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def balancesheet(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.balance_sheet_statement.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare.balance_sheet_statement import fetch_balance_sheet_statement

    result = fetch_balance_sheet_statement(
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        period="20241231",
        report_type="1",
        fields="ts_code,end_date,total_assets",
    )

    assert fake_pro.calls == [
        {
            "ts_code": "600000.SH",
            "start_date": "20240101",
            "end_date": "20241231",
            "period": "20241231",
            "report_type": "1",
            "fields": "ts_code,end_date,total_assets",
        }
    ]
    assert result.equals(expected_df)


def test_tushare_balance_sheet_uses_all_fields_by_default(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def balancesheet(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.balance_sheet_statement.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare.balance_sheet_statement import (
        BALANCE_SHEET_ALL_FIELDS,
        fetch_balance_sheet_statement,
    )

    result = fetch_balance_sheet_statement(ts_code="600000.SH")

    assert fake_pro.calls == [{"ts_code": "600000.SH", "fields": BALANCE_SHEET_ALL_FIELDS}]
    assert result.equals(expected_df)


def test_tushare_cash_flow_uses_filtered_query_params(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def cashflow(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.cash_flow_statement.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare.cash_flow_statement import fetch_cash_flow_statement

    result = fetch_cash_flow_statement(
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        period="20241231",
        report_type="1",
        is_calc=1,
        fields="ts_code,end_date,n_cashflow_act",
    )

    assert fake_pro.calls == [
        {
            "ts_code": "600000.SH",
            "start_date": "20240101",
            "end_date": "20241231",
            "period": "20241231",
            "report_type": "1",
            "is_calc": 1,
            "fields": "ts_code,end_date,n_cashflow_act",
        }
    ]
    assert result.equals(expected_df)


def test_tushare_cash_flow_uses_all_fields_by_default(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600000.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def cashflow(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.cash_flow_statement.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare.cash_flow_statement import (
        CASH_FLOW_ALL_FIELDS,
        fetch_cash_flow_statement,
    )

    result = fetch_cash_flow_statement(ts_code="600000.SH")

    assert fake_pro.calls == [{"ts_code": "600000.SH", "fields": CASH_FLOW_ALL_FIELDS}]
    assert result.equals(expected_df)


def test_tushare_fetchers_use_exchange_specific_queries(monkeypatch):
    calls = []

    def fake_fetch_stock_list(exchange):
        calls.append(exchange)
        return pd.DataFrame({"exchange": [exchange]})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_basic._fetch_stock_list",
        fake_fetch_stock_list,
    )

    from data_fetch.sources.tushare import fetch_sh_stock_list, fetch_sz_stock_list

    sh_result = fetch_sh_stock_list()
    sz_result = fetch_sz_stock_list()

    assert calls == ["SSE", "SZSE"]
    assert sh_result.loc[0, "exchange"] == "SSE"
    assert sz_result.loc[0, "exchange"] == "SZSE"


def test_tushare_stock_company_uses_exchange_specific_queries(monkeypatch):
    calls = []

    class FakePro:
        def stock_company(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({"exchange": [kwargs["exchange"]]})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_company.build_tushare_clients",
        lambda: (object(), FakePro()),
    )

    from data_fetch.sources.tushare import fetch_sh_stock_company, fetch_sz_stock_company

    sh_result = fetch_sh_stock_company()
    sz_result = fetch_sz_stock_company()

    assert calls == [
        {
            "exchange": "SSE",
            "fields": (
                "ts_code,com_name,com_id,exchange,chairman,manager,secretary,reg_capital,"
                "setup_date,province,city,introduction,website,email,office,employees,"
                "main_business,business_scope"
            ),
        },
        {
            "exchange": "SZSE",
            "fields": (
                "ts_code,com_name,com_id,exchange,chairman,manager,secretary,reg_capital,"
                "setup_date,province,city,introduction,website,email,office,employees,"
                "main_business,business_scope"
            ),
        },
    ]
    assert sh_result.loc[0, "exchange"] == "SSE"
    assert sz_result.loc[0, "exchange"] == "SZSE"


def test_tushare_stock_st_uses_trade_date(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["600289.SH"]})

    class FakePro:
        def __init__(self):
            self.calls = []

        def stock_st(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_pro = FakePro()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_st.build_tushare_clients",
        lambda: (object(), fake_pro),
    )

    from data_fetch.sources.tushare import fetch_stock_st_list

    result = fetch_stock_st_list("20260320")

    assert fake_pro.calls == [
        {
            "trade_date": "20260320",
            "fields": "ts_code,name,trade_date,type,type_name",
        }
    ]
    assert result.equals(expected_df)


def test_tushare_trade_calendar_fetches_sse_and_szse(monkeypatch):
    calls = []

    class FakePro:
        def trade_cal(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({"exchange": [kwargs["exchange"]], "cal_date": [kwargs["start_date"]]})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.trade_calendar.build_tushare_clients",
        lambda: (object(), FakePro()),
    )

    from data_fetch.sources.tushare import fetch_trade_calendar

    result = fetch_trade_calendar("20260320", "20260320")

    assert calls == [
        {
            "exchange": "SSE",
            "start_date": "20260320",
            "end_date": "20260320",
            "fields": "exchange,cal_date,is_open,pretrade_date",
        },
        {
            "exchange": "SZSE",
            "start_date": "20260320",
            "end_date": "20260320",
            "fields": "exchange,cal_date,is_open,pretrade_date",
        },
    ]
    assert result["exchange"].tolist() == ["SSE", "SZSE"]


def test_tushare_index_basic_fetches_all_markets(monkeypatch):
    calls = []

    class FakePro:
        def index_basic(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({"market": [kwargs["market"]], "ts_code": [f'{kwargs["market"]}.000001']})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.index_basic.build_tushare_clients",
        lambda: (object(), FakePro()),
    )

    from data_fetch.sources.tushare import fetch_index_basic

    result = fetch_index_basic()

    assert calls == [
        {
            "market": "CSI",
            "fields": "ts_code,name,fullname,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date",
        },
        {
            "market": "SSE",
            "fields": "ts_code,name,fullname,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date",
        },
        {
            "market": "SZSE",
            "fields": "ts_code,name,fullname,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date",
        },
    ]
    assert result["market"].tolist() == ["CSI", "SSE", "SZSE"]


def test_filter_stock_index_basic_keeps_stock_categories_only():
    index_basic_df = pd.DataFrame(
        {
            "ts_code": ["000001.SH", "AU9999.SGE", "801010.SI"],
            "market": ["CSI", "OTH", "SW"],
            "category": ["规模指数", "贵金属指数", "行业指数"],
        }
    )

    result = filter_stock_index_basic(index_basic_df)

    assert result["ts_code"].tolist() == ["000001.SH", "801010.SI"]
    assert result["category"].tolist() == ["规模指数", "行业指数"]


def test_tushare_index_basic_uses_runtime_markets(monkeypatch, tmp_path):
    calls = []

    class FakePro:
        def index_basic(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({"market": [kwargs["market"]]})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.index_basic.build_tushare_clients",
        lambda: (object(), FakePro()),
    )
    monkeypatch.setattr(
        "data_fetch.sources.tushare.index_basic.get_default_index_basic_markets",
        lambda: ("MSCI", "SW"),
    )

    from data_fetch.sources.tushare import fetch_index_basic

    result = fetch_index_basic()

    assert calls == [
        {
            "market": "MSCI",
            "fields": "ts_code,name,fullname,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date",
        },
        {
            "market": "SW",
            "fields": "ts_code,name,fullname,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date",
        },
    ]
    assert result["market"].tolist() == ["MSCI", "SW"]


def test_filter_stock_index_basic_uses_runtime_categories(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "data_fetch.sources.tushare.index_basic.get_default_stock_index_basic_categories",
        lambda: ("主题指数", "策略指数"),
    )

    index_basic_df = pd.DataFrame(
        {
            "ts_code": ["000001.SH", "000002.SH", "801010.SI"],
            "market": ["CSI", "CSI", "SW"],
            "category": ["规模指数", "主题指数", "策略指数"],
        }
    )

    result = filter_stock_index_basic(index_basic_df)

    assert result["ts_code"].tolist() == ["000002.SH", "801010.SI"]
    assert result["category"].tolist() == ["主题指数", "策略指数"]


def test_tushare_index_weight_forwards_expected_fields(monkeypatch):
    calls = []

    class FakePro:
        def index_weight(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({"index_code": [kwargs["index_code"]], "trade_date": [kwargs["start_date"]]})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.index_weight.build_tushare_clients",
        lambda: (object(), FakePro()),
    )

    from data_fetch.sources.tushare import fetch_index_weight

    result = fetch_index_weight(
        index_code="399300.SZ",
    )

    assert calls == [
        {
            "index_code": "399300.SZ",
            "start_date": None,
            "end_date": None,
            "fields": "index_code,con_code,trade_date,weight",
        }
    ]
    assert result["index_code"].tolist() == ["399300.SZ"]


def test_tushare_stock_hsgt_fetches_hk_sz_and_hk_sh(monkeypatch):
    calls = []

    class FakePro:
        def stock_hsgt(self, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame({"type": [kwargs["type"]], "ts_code": ["000001.SZ"]})

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_hsgt.build_tushare_clients",
        lambda: (object(), FakePro()),
    )

    from data_fetch.sources.tushare import fetch_stock_hsgt_list

    result = fetch_stock_hsgt_list("20260320", "20260321")

    assert calls == [
        {
            "type": "HK_SZ",
            "start_date": "20260320",
            "end_date": "20260321",
            "fields": "ts_code,trade_date,type,name,type_name",
        },
        {
            "type": "HK_SH",
            "start_date": "20260320",
            "end_date": "20260321",
            "fields": "ts_code,trade_date,type,name,type_name",
        },
    ]
    assert result["type"].tolist() == ["HK_SZ", "HK_SH"]


def test_tushare_stock_qfq_daily_uses_pro_bar_fixed_params(monkeypatch):
    expected_df = pd.DataFrame(
        {
            "ts_code": ["000001.SZ"],
            "trade_date": ["20240102"],
            "open": [10.0],
            "high": [10.5],
            "low": [9.8],
            "close": [10.2],
            "pre_close": [9.9],
            "change": [0.3],
            "pct_chg": [3.03],
            "vol": [1000.0],
            "amount": [10200.0],
            "extra_col": ["ignored"],
        }
    )

    class FakeTs:
        def __init__(self):
            self.calls = []

        def pro_bar(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_ts = FakeTs()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_qfq_daily.build_tushare_clients",
        lambda: (fake_ts, object()),
    )

    from data_fetch.sources.tushare import fetch_stock_qfq_daily

    result = fetch_stock_qfq_daily(
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    )

    assert fake_ts.calls == [
        {
            "ts_code": "000001.SZ",
            "start_date": "20240101",
            "end_date": "20241231",
            "asset": "E",
            "adj": "qfq",
            "freq": "D",
        }
    ]
    assert result.columns.tolist() == [
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
    assert result.loc[0, "ts_code"] == "000001.SZ"


def test_tushare_stock_qfq_5min_uses_pro_bar_fixed_params(monkeypatch):
    expected_df = pd.DataFrame(
        {
            "ts_code": ["000001.SZ"],
            "trade_time": ["2024-01-02 09:35:00"],
            "open": [10.0],
            "close": [10.2],
            "high": [10.3],
            "low": [9.9],
            "vol": [10000],
            "amount": [102000.0],
            "extra_col": ["ignored"],
        }
    )

    class FakeTs:
        def __init__(self):
            self.calls = []

        def pro_bar(self, **kwargs):
            self.calls.append(kwargs)
            return expected_df

    fake_ts = FakeTs()

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_qfq_5min.build_tushare_clients",
        lambda: (fake_ts, object()),
    )

    from data_fetch.sources.tushare import fetch_stock_qfq_5min

    result = fetch_stock_qfq_5min(
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    )

    assert fake_ts.calls == [
        {
            "ts_code": "000001.SZ",
            "start_date": "20240101",
            "end_date": "20241231",
            "asset": "E",
            "adj": "qfq",
            "freq": "5MIN",
        }
    ]
    assert result.columns.tolist() == [
        "ts_code",
        "trade_time",
        "open",
        "close",
        "high",
        "low",
        "vol",
        "amount",
    ]
    assert result.loc[0, "ts_code"] == "000001.SZ"


def test_tushare_stock_daily_basic_uses_pro_daily_basic(monkeypatch):
    expected_df = pd.DataFrame({"ts_code": ["000001.SZ"]})
    calls = []

    class FakePro:
        def daily_basic(self, **kwargs):
            calls.append(kwargs)
            return expected_df

    monkeypatch.setattr(
        "data_fetch.sources.tushare.stock_daily_basic.build_tushare_clients",
        lambda: (object(), FakePro()),
    )

    from data_fetch.sources.tushare import fetch_stock_daily_basic

    result = fetch_stock_daily_basic(
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    )

    assert calls == [
        {
            "ts_code": "000001.SZ",
            "start_date": "20240101",
            "end_date": "20241231",
        }
    ]
    assert result.equals(expected_df)


def test_build_default_fetcher_supports_tushare_source():
    fetcher = build_default_fetcher()

    assert fetcher.provider.source_name == TUSHARE_SOURCE


def test_data_path_manager_builds_default_paths(tmp_path):
    assert build_company_basic_info_path(base_dir=tmp_path, today_ymd="20260322", exchange="SSE") == (
        tmp_path / "20260322" / "company" / "company_basic_info" / "sh_company_basic_info.csv"
    )
    assert build_index_basic_source_dir(base_dir=tmp_path, today_ymd="20260322", market="SSE") == (
        tmp_path / "20260322" / "index" / "index_basic" / "sse"
    )
    assert build_index_basic_path(base_dir=tmp_path, today_ymd="20260322", market="SSE", category="规模指数") == (
        tmp_path / "20260322" / "index" / "index_basic" / "sse" / "规模指数" / "sse_规模指数_index_basic.csv"
    )
    assert build_trade_calendar_path(
        base_dir=tmp_path, today_ymd="20260322", start_date="20180101", end_date="20260322"
    ) == (
        tmp_path / "20260322" / "calendar" / "calendar" / "calendar_20180101_20260322.csv"
    )
    assert build_index_weight_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        index_code="399300.SZ",
    ) == (
        tmp_path
        / "20260322"
        / "index"
        / "index_weight"
        / "index_weight_399300_sz.csv"
    )
    assert build_stock_list_path(base_dir=tmp_path, today_ymd="20260322", exchange="SZSE") == (
        tmp_path / "20260322" / "stock" / "stock_list" / "sz_stock_list.csv"
    )
    assert build_quote_qfq_daily_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    ) == (
        tmp_path
        / "20260322"
        / "quote"
        / "qfq_daily"
        / "sz_000001_qfq_daily_20240101_20241231.csv"
    )
    assert build_quote_qfq_5min_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    ) == (
        tmp_path
        / "20260322"
        / "quote"
        / "qfq_5min"
        / "sz_000001_qfq_5min_20240101_20241231.csv"
    )
    assert build_quote_daily_basic_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        ts_code="000001.SZ",
        start_date="20240101",
        end_date="20241231",
    ) == (
        tmp_path
        / "20260322"
        / "quote"
        / "daily_basic"
        / "sz_000001_daily_basic_20240101_20241231.csv"
    )


def test_data_path_manager_builds_financial_statement_paths(tmp_path):
    balancesheet_path = build_financial_statement_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        statement_type="balancesheet",
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        report_type="1",
    )
    cashflow_path = build_financial_statement_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        statement_type="cashflow",
        ts_code="600000.SH",
        start_date="20240101",
        end_date="20241231",
        report_type="1",
        is_calc=1,
    )
    income_path = build_financial_statement_path(
        base_dir=tmp_path,
        today_ymd="20260322",
        statement_type="income",
        ts_code="600000.SH",
        period="20241231",
        report_type="1",
        comp_type="2",
    )

    assert balancesheet_path == (
        tmp_path
        / "20260322"
        / "company"
        / "financial"
        / "balancesheet"
        / "sh_600000_balancesheet_20240101_20241231_report_1.csv"
    )
    assert cashflow_path == (
        tmp_path
        / "20260322"
        / "company"
        / "financial"
        / "cashflow"
        / "sh_600000_cashflow_20240101_20241231_report_1_calc_1.csv"
    )
    assert income_path == (
        tmp_path
        / "20260322"
        / "company"
        / "financial"
        / "income"
        / "sh_600000_income_20241231_report_1_comp_2.csv"
    )


def test_data_path_manager_checks_current_data(tmp_path):
    output_path = build_stock_st_list_path(base_dir=tmp_path, today_ymd="20260322")

    pd.DataFrame({"ts_code": ["600289.SH"]}).to_csv(output_path, index=False, encoding="utf-8-sig")

    assert has_current_data(output_path)
    saved_df = pd.read_csv(output_path)
    assert saved_df["ts_code"].tolist() == ["600289.SH"]


def test_data_path_manager_checks_current_index_basic_data(tmp_path):
    output_path = build_index_basic_path(base_dir=tmp_path, today_ymd="20260322", market="CSI", category="规模指数")

    pd.DataFrame({"ts_code": ["000001.SH"]}).to_csv(output_path, index=False, encoding="utf-8-sig")

    assert has_current_index_basic_data(base_dir=tmp_path, today_ymd="20260322", market="CSI")


def test_cli_exits_when_tushare_token_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "tushare":
            return object()
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    args = cli.build_parser().parse_args(["--output-dir", str(tmp_path)])

    with pytest.raises(SystemExit, match="缺少环境变量 TUSHARE_TOKEN"):
        cli.run(args)


def test_cli_requires_token_even_when_today_files_exist(tmp_path, monkeypatch):
    today_ymd = datetime.today().strftime("%Y%m%d")
    default_start_date = get_default_fetch_start_date()
    default_index_codes = DEFAULT_INDEX_CODES
    dated_root = tmp_path / today_ymd
    company_basic_info_dir = dated_root / "company" / "company_basic_info"
    index_basic_dir = dated_root / "index" / "index_basic"
    index_weight_dir = dated_root / "index" / "index_weight"
    trade_calendar_dir = dated_root / "calendar" / "calendar"
    hsgt_stock_list_dir = dated_root / "stock" / "hsgt_stock_list"
    stock_list_dir = dated_root / "stock" / "stock_list"
    st_stock_list_dir = dated_root / "stock" / "st_stock_list"
    company_basic_info_dir.mkdir(parents=True)
    index_basic_dir.mkdir(parents=True)
    index_weight_dir.mkdir(parents=True)
    trade_calendar_dir.mkdir(parents=True)
    hsgt_stock_list_dir.mkdir(parents=True)
    stock_list_dir.mkdir(parents=True)
    st_stock_list_dir.mkdir(parents=True)

    (company_basic_info_dir / "sh_company_basic_info.csv").write_text(
        "ts_code\n600000.SH\n"
    )
    (company_basic_info_dir / "sz_company_basic_info.csv").write_text(
        "ts_code\n000001.SZ\n"
    )
    for market, category in (
        ("MSCI", "规模指数"),
        ("CSI", "规模指数"),
        ("SSE", "综合指数"),
        ("SZSE", "综合指数"),
        ("CICC", "策略指数"),
        ("SW", "行业指数"),
        ("OTH", "主题指数"),
    ):
        index_basic_path = (
            index_basic_dir
            / market.lower()
            / category
            / f"{market.lower()}_{category}_index_basic.csv"
        )
        index_basic_path.parent.mkdir(parents=True, exist_ok=True)
        index_basic_path.write_text(
            f"ts_code,market,category\n000001.SH,{market},{category}\n"
        )
    for index_code in default_index_codes:
        normalized_index_code = index_code.replace(".", "_").lower()
        (
            index_weight_dir
            / f"index_weight_{normalized_index_code}.csv"
        ).write_text(f"index_code,con_code,trade_date,weight\n{index_code},000001.SZ,{today_ymd},1.0\n")
    (trade_calendar_dir / f"calendar_{default_start_date}_{today_ymd}.csv").write_text(
        "exchange,cal_date,is_open,pretrade_date\nSSE,20260320,1,20260319\n"
    )
    (hsgt_stock_list_dir / f"hsgt_stock_list_{default_start_date}_{today_ymd}.csv").write_text(
        "ts_code,trade_date,type,name,type_name\n000001.SZ,20260320,HK_SZ,平安银行,深股通(港>深)\n"
    )
    (stock_list_dir / "sh_stock_list.csv").write_text("ts_code\n600000.SH\n")
    (stock_list_dir / "sz_stock_list.csv").write_text("ts_code\n000001.SZ\n")
    (st_stock_list_dir / "st_stock_list.csv").write_text("ts_code\n600289.SH\n")

    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    args = cli.build_parser().parse_args(["--output-dir", str(tmp_path)])

    with pytest.raises(SystemExit, match="缺少环境变量 TUSHARE_TOKEN"):
        cli.run(args)


def test_cli_without_args_fetches_default_financial_statements(tmp_path, monkeypatch):
    today_ymd = datetime.today().strftime("%Y%m%d")
    default_start_date = get_default_fetch_start_date()
    default_index_codes = DEFAULT_INDEX_CODES
    financial_ts_code = DEFAULT_TS_CODES[0]
    call_order = []
    balancesheet_calls = []
    income_calls = []
    cashflow_calls = []
    qfq_daily_calls = []
    qfq_5min_calls = []
    daily_basic_calls = []
    index_weight_calls = []
    runtime_write_calls = []

    class FakeFetcher:
        def fetch_company_balancesheet(self, **kwargs):
            call_order.append("company.balancesheet")
            balancesheet_calls.append(kwargs)
            return FetchResult(
                data=pd.DataFrame({"ts_code": [kwargs["ts_code"]], "end_date": [kwargs["end_date"]]})
            )

        def fetch_company_income(self, **kwargs):
            call_order.append("company.income")
            income_calls.append(kwargs)
            return FetchResult(
                data=pd.DataFrame({"ts_code": [kwargs["ts_code"]], "end_date": [kwargs["end_date"]]})
            )

        def fetch_company_cashflow(self, **kwargs):
            call_order.append("company.cashflow")
            cashflow_calls.append(kwargs)
            return FetchResult(
                data=pd.DataFrame({"ts_code": [kwargs["ts_code"]], "end_date": [kwargs["end_date"]]})
            )

        def fetch_company_basic_info(self, **kwargs):
            call_order.append("company.basic_info")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_trade_calendar(self, **kwargs):
            call_order.append("market.trade_calendar")
            return FetchResult(data=pd.DataFrame({"cal_date": [today_ymd]}))

        def fetch_market_index_basic(self):
            call_order.append("market.index_basic")
            return FetchResult(
                data=pd.DataFrame(
                    {
                        "ts_code": [
                            "MSCI.000001",
                            "CSI.000001",
                            "SSE.000001",
                            "SZSE.000001",
                            "CICC.000001",
                            "SW.000001",
                            "OTH.000001",
                            "AU9999.SGE",
                        ],
                        "market": ["MSCI", "CSI", "SSE", "SZSE", "CICC", "SW", "OTH", "OTH"],
                        "category": [
                            "规模指数",
                            "规模指数",
                            "综合指数",
                            "综合指数",
                            "策略指数",
                            "行业指数",
                            "主题指数",
                            "贵金属指数",
                        ],
                    }
                )
            )

        def fetch_market_index_weight(self, **kwargs):
            call_order.append("market.index_weight")
            index_weight_calls.append(kwargs)
            return FetchResult(
                data=pd.DataFrame(
                    {
                        "index_code": [kwargs["index_code"]],
                        "con_code": ["000001.SZ"],
                        "trade_date": [kwargs.get("end_date", today_ymd)],
                        "weight": [1.0],
                    }
                )
            )

        def fetch_stock_hsgt_list(self, **kwargs):
            call_order.append("stock.hsgt_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["000001.SZ"]}))

        def fetch_stock_list(self, **kwargs):
            call_order.append("stock.list")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_stock_qfq_daily(self, **kwargs):
            call_order.append("stock.qfq_daily")
            qfq_daily_calls.append(kwargs)
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_stock_qfq_5min(self, **kwargs):
            call_order.append("stock.qfq_5min")
            qfq_5min_calls.append(kwargs)
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_stock_daily_basic(self, **kwargs):
            call_order.append("stock.daily_basic")
            daily_basic_calls.append(kwargs)
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_st_stock_list(self, **kwargs):
            call_order.append("stock.st_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["600289.SH"]}))

    monkeypatch.setattr(cli, "get_runtime_ts_codes", lambda: (financial_ts_code,))
    monkeypatch.setattr(cli, "get_default_index_codes", lambda: default_index_codes)
    monkeypatch.setattr(
        cli,
        "write_runtime_targets",
        lambda **kwargs: runtime_write_calls.append(kwargs) or (tmp_path / "runtime" / "targets.json"),
    )
    monkeypatch.setattr(cli, "build_default_fetcher", lambda: FakeFetcher())

    args = cli.build_parser().parse_args(["--output-dir", str(tmp_path)])

    cli.run_inner(args)

    assert call_order == [
        "market.index_basic",
        "market.index_weight",
        "market.index_weight",
        "stock.hsgt_list",
        "stock.list",
        "stock.st_list",
        "stock.qfq_daily",
        "stock.qfq_5min",
        "stock.daily_basic",
        "company.basic_info",
        "company.balancesheet",
        "company.income",
        "company.cashflow",
        "market.trade_calendar",
    ]

    assert balancesheet_calls == [
        {
            "ts_code": financial_ts_code,
            "ann_date": None,
            "start_date": default_start_date,
            "end_date": today_ymd,
            "period": None,
            "report_type": None,
            "comp_type": None,
            "fields": None,
        }
    ]
    assert income_calls == [
        {
            "ts_code": financial_ts_code,
            "ann_date": None,
            "f_ann_date": None,
            "start_date": default_start_date,
            "end_date": today_ymd,
            "period": None,
            "report_type": None,
            "comp_type": None,
            "fields": None,
        }
    ]
    assert cashflow_calls == [
        {
            "ts_code": financial_ts_code,
            "ann_date": None,
            "f_ann_date": None,
            "start_date": default_start_date,
            "end_date": today_ymd,
            "period": None,
            "report_type": None,
            "comp_type": None,
            "is_calc": None,
            "fields": None,
        }
    ]
    assert qfq_daily_calls == [
        {
            "ts_code": financial_ts_code,
            "start_date": default_start_date,
            "end_date": today_ymd,
        }
    ]
    assert qfq_5min_calls == [
        {
            "ts_code": financial_ts_code,
            "start_date": default_start_date,
            "end_date": today_ymd,
        }
    ]
    assert daily_basic_calls == [
        {
            "ts_code": financial_ts_code,
            "start_date": default_start_date,
            "end_date": today_ymd,
        }
    ]
    assert index_weight_calls == [
        {
            "index_code": "399300.SZ",
        },
        {
            "index_code": "000001.SH",
        },
    ]
    assert (
        tmp_path / today_ymd / "index" / "index_basic" / "csi" / "规模指数" / "csi_规模指数_index_basic.csv"
    ).exists()
    assert (
        tmp_path / today_ymd / "index" / "index_basic" / "sse" / "综合指数" / "sse_综合指数_index_basic.csv"
    ).exists()
    assert (
        tmp_path / today_ymd / "index" / "index_basic" / "szse" / "综合指数" / "szse_综合指数_index_basic.csv"
    ).exists()
    assert not (
        tmp_path / today_ymd / "index" / "index_basic" / "oth" / "贵金属指数" / "oth_贵金属指数_index_basic.csv"
    ).exists()
    assert (
        tmp_path
        / today_ymd
        / "index"
        / "index_weight"
        / "index_weight_399300_sz.csv"
    ).exists()
    assert (
        tmp_path
        / today_ymd
        / "index"
        / "index_weight"
        / "index_weight_000001_sh.csv"
    ).exists()
    assert (
        tmp_path
        / today_ymd
        / "company"
        / "financial"
        / "balancesheet"
        / f"sh_600000_balancesheet_{default_start_date}_{today_ymd}.csv"
    ).exists()
    assert (
        tmp_path
        / today_ymd
        / "quote"
        / "qfq_daily"
        / f"sh_600000_qfq_daily_{default_start_date}_{today_ymd}.csv"
    ).exists()
    assert (
        tmp_path
        / today_ymd
        / "quote"
        / "qfq_5min"
        / f"sh_600000_qfq_5min_{default_start_date}_{today_ymd}.csv"
    ).exists()
    assert (
        tmp_path
        / today_ymd
        / "quote"
        / "daily_basic"
        / f"sh_600000_daily_basic_{default_start_date}_{today_ymd}.csv"
    ).exists()
    assert runtime_write_calls == [
        {
            "ts_codes": ["600000.SH", "000001.SZ"],
            "index_codes": ["399300.SZ", "000001.SH"],
            "index_basic_markets": ["CSI", "SSE", "SZSE"],
            "stock_index_basic_categories": [
                "主题指数",
                "规模指数",
                "策略指数",
                "风格指数",
                "综合指数",
                "行业指数",
            ],
        }
    ]


def test_cli_without_runtime_ts_codes_skips_financial_fetch(tmp_path, monkeypatch):
    today_ymd = datetime.today().strftime("%Y%m%d")
    call_order = []

    class FakeFetcher:
        def fetch_company_balancesheet(self, **kwargs):
            raise AssertionError("financial fetch should be skipped when runtime ts_codes is empty")

        def fetch_company_income(self, **kwargs):
            raise AssertionError("financial fetch should be skipped when runtime ts_codes is empty")

        def fetch_company_cashflow(self, **kwargs):
            raise AssertionError("financial fetch should be skipped when runtime ts_codes is empty")

        def fetch_company_basic_info(self, **kwargs):
            call_order.append("company.basic_info")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_trade_calendar(self, **kwargs):
            call_order.append("market.trade_calendar")
            return FetchResult(data=pd.DataFrame({"cal_date": [today_ymd]}))

        def fetch_market_index_basic(self):
            call_order.append("market.index_basic")
            return FetchResult(
                data=pd.DataFrame(
                    {
                        "ts_code": ["CSI.000001"],
                        "market": ["CSI"],
                        "category": ["规模指数"],
                    }
                )
            )

        def fetch_market_index_weight(self, **kwargs):
            call_order.append("market.index_weight")
            return FetchResult(
                data=pd.DataFrame(
                    {
                        "index_code": [kwargs["index_code"]],
                        "con_code": ["000001.SZ"],
                        "trade_date": [today_ymd],
                        "weight": [1.0],
                    }
                )
            )

        def fetch_stock_hsgt_list(self, **kwargs):
            call_order.append("stock.hsgt_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["000001.SZ"]}))

        def fetch_stock_list(self, **kwargs):
            call_order.append("stock.list")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_stock_qfq_daily(self, **kwargs):
            raise AssertionError("qfq_daily fetch should be skipped when runtime ts_codes is empty")

        def fetch_stock_qfq_5min(self, **kwargs):
            raise AssertionError("qfq_5min fetch should be skipped when runtime ts_codes is empty")

        def fetch_stock_daily_basic(self, **kwargs):
            raise AssertionError("daily_basic fetch should be skipped when runtime ts_codes is empty")

        def fetch_st_stock_list(self, **kwargs):
            call_order.append("stock.st_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["600289.SH"]}))

    monkeypatch.setattr(cli, "get_runtime_ts_codes", lambda: ())
    monkeypatch.setattr(cli, "get_default_index_codes", lambda: ())
    monkeypatch.setattr(cli, "get_default_index_basic_markets", lambda: ("CSI",))
    monkeypatch.setattr(cli, "build_default_fetcher", lambda: FakeFetcher())

    args = cli.build_parser().parse_args(["--output-dir", str(tmp_path)])

    cli.run_inner(args)

    assert call_order == [
        "market.index_basic",
        "stock.hsgt_list",
        "stock.list",
        "stock.st_list",
        "company.basic_info",
        "market.trade_calendar",
    ]


def test_cli_with_skip_financial_skips_financial_fetch_even_when_runtime_has_ts_codes(tmp_path, monkeypatch):
    today_ymd = datetime.today().strftime("%Y%m%d")
    call_order = []

    class FakeFetcher:
        def fetch_company_balancesheet(self, **kwargs):
            raise AssertionError("financial fetch should be skipped when --skip-financial is set")

        def fetch_company_income(self, **kwargs):
            raise AssertionError("financial fetch should be skipped when --skip-financial is set")

        def fetch_company_cashflow(self, **kwargs):
            raise AssertionError("financial fetch should be skipped when --skip-financial is set")

        def fetch_company_basic_info(self, **kwargs):
            call_order.append("company.basic_info")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_trade_calendar(self, **kwargs):
            call_order.append("market.trade_calendar")
            return FetchResult(data=pd.DataFrame({"cal_date": [today_ymd]}))

        def fetch_market_index_basic(self):
            call_order.append("market.index_basic")
            return FetchResult(
                data=pd.DataFrame(
                    {
                        "ts_code": ["CSI.000001"],
                        "market": ["CSI"],
                        "category": ["规模指数"],
                    }
                )
            )

        def fetch_market_index_weight(self, **kwargs):
            call_order.append("market.index_weight")
            return FetchResult(
                data=pd.DataFrame(
                    {
                        "index_code": [kwargs["index_code"]],
                        "con_code": ["000001.SZ"],
                        "trade_date": [today_ymd],
                        "weight": [1.0],
                    }
                )
            )

        def fetch_stock_hsgt_list(self, **kwargs):
            call_order.append("stock.hsgt_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["000001.SZ"]}))

        def fetch_stock_list(self, **kwargs):
            call_order.append("stock.list")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_stock_qfq_daily(self, **kwargs):
            call_order.append("stock.qfq_daily")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_stock_qfq_5min(self, **kwargs):
            call_order.append("stock.qfq_5min")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_stock_daily_basic(self, **kwargs):
            call_order.append("stock.daily_basic")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_st_stock_list(self, **kwargs):
            call_order.append("stock.st_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["600289.SH"]}))

    monkeypatch.setattr(cli, "get_runtime_ts_codes", lambda: ("600000.SH",))
    monkeypatch.setattr(cli, "get_default_index_codes", lambda: ())
    monkeypatch.setattr(cli, "get_default_index_basic_markets", lambda: ("CSI",))
    monkeypatch.setattr(cli, "build_default_fetcher", lambda: FakeFetcher())

    args = cli.build_parser().parse_args(["--output-dir", str(tmp_path), "--skip-financial"])

    cli.run_inner(args)

    assert call_order == [
        "market.index_basic",
        "stock.hsgt_list",
        "stock.list",
        "stock.st_list",
        "stock.qfq_daily",
        "stock.qfq_5min",
        "stock.daily_basic",
        "company.basic_info",
        "market.trade_calendar",
    ]


def test_cli_with_skip_qfq_flags_skips_quote_fetch_even_when_runtime_has_ts_codes(tmp_path, monkeypatch):
    today_ymd = datetime.today().strftime("%Y%m%d")
    call_order = []

    class FakeFetcher:
        def fetch_company_balancesheet(self, **kwargs):
            call_order.append("company.balancesheet")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_company_income(self, **kwargs):
            call_order.append("company.income")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_company_cashflow(self, **kwargs):
            call_order.append("company.cashflow")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_company_basic_info(self, **kwargs):
            call_order.append("company.basic_info")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_trade_calendar(self, **kwargs):
            call_order.append("market.trade_calendar")
            return FetchResult(data=pd.DataFrame({"cal_date": [today_ymd]}))

        def fetch_market_index_basic(self):
            call_order.append("market.index_basic")
            return FetchResult(data=pd.DataFrame({"ts_code": ["CSI.000001"], "market": ["CSI"], "category": ["规模指数"]}))

        def fetch_market_index_weight(self, **kwargs):
            call_order.append("market.index_weight")
            return FetchResult(
                data=pd.DataFrame(
                    {"index_code": [kwargs["index_code"]], "con_code": ["000001.SZ"], "trade_date": [today_ymd], "weight": [1.0]}
                )
            )

        def fetch_stock_hsgt_list(self, **kwargs):
            call_order.append("stock.hsgt_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["000001.SZ"]}))

        def fetch_stock_list(self, **kwargs):
            call_order.append("stock.list")
            return FetchResult(
                data={
                    "sh": pd.DataFrame({"ts_code": ["600000.SH"]}),
                    "sz": pd.DataFrame({"ts_code": ["000001.SZ"]}),
                }
            )

        def fetch_stock_qfq_daily(self, **kwargs):
            raise AssertionError("qfq_daily fetch should be skipped when --skip-qfq-daily is set")

        def fetch_stock_qfq_5min(self, **kwargs):
            raise AssertionError("qfq_5min fetch should be skipped when --skip-qfq-5min is set")

        def fetch_stock_daily_basic(self, **kwargs):
            call_order.append("stock.daily_basic")
            return FetchResult(data=pd.DataFrame({"ts_code": [kwargs["ts_code"]]}))

        def fetch_st_stock_list(self, **kwargs):
            call_order.append("stock.st_list")
            return FetchResult(data=pd.DataFrame({"ts_code": ["600289.SH"]}))

    monkeypatch.setattr(cli, "get_runtime_ts_codes", lambda: ("600000.SH",))
    monkeypatch.setattr(cli, "get_default_index_codes", lambda: ())
    monkeypatch.setattr(cli, "get_default_index_basic_markets", lambda: ("CSI",))
    monkeypatch.setattr(cli, "build_default_fetcher", lambda: FakeFetcher())

    args = cli.build_parser().parse_args(["--output-dir", str(tmp_path), "--skip-qfq-daily", "--skip-qfq-5min"])

    cli.run_inner(args)

    assert call_order == [
        "market.index_basic",
        "stock.hsgt_list",
        "stock.list",
        "stock.st_list",
        "stock.daily_basic",
        "company.basic_info",
        "company.balancesheet",
        "company.income",
        "company.cashflow",
        "market.trade_calendar",
    ]


def test_get_default_codes_use_config_constants_when_runtime_missing():
    assert get_default_ts_codes() == DEFAULT_TS_CODES
    assert get_default_index_codes() == DEFAULT_INDEX_CODES
    assert get_runtime_ts_codes() == ()


def test_runtime_targets_file_overrides_env_defaults(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "targets.json").write_text(
        json.dumps(
            {
                "ts_codes": ["600519.sh", "000001.sz", "600519.SH"],
                "index_codes": ["399300.sz", "000001.sh"],
                "index_basic_markets": ["sw", "csi"],
                "stock_index_basic_categories": ["主题指数", "行业指数", "主题指数"],
            }
        ),
        encoding="utf-8",
    )
    assert get_default_ts_codes(project_root=tmp_path) == ("600519.SH", "000001.SZ")
    assert get_runtime_ts_codes(project_root=tmp_path) == ("600519.SH", "000001.SZ")
    assert get_default_index_codes(project_root=tmp_path) == ("399300.SZ", "000001.SH")
    assert get_default_index_basic_markets(project_root=tmp_path) == ("SW", "CSI")
    assert get_default_stock_index_basic_categories(project_root=tmp_path) == ("主题指数", "行业指数")


def test_runtime_targets_missing_fields_fallback_to_env(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "targets.json").write_text(
        json.dumps({"ts_codes": ["600519.SH"]}),
        encoding="utf-8",
    )
    assert get_default_ts_codes(project_root=tmp_path) == ("600519.SH",)
    assert get_runtime_ts_codes(project_root=tmp_path) == ("600519.SH",)
    assert get_default_index_codes(project_root=tmp_path) == DEFAULT_INDEX_CODES
    assert get_default_index_basic_markets(project_root=tmp_path) == ("CSI", "SSE", "SZSE")
    assert get_default_stock_index_basic_categories(project_root=tmp_path) == (
        "主题指数",
        "规模指数",
        "策略指数",
        "风格指数",
        "综合指数",
        "行业指数",
    )


def test_runtime_targets_can_explicitly_disable_default_targets(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir(parents=True)
    (runtime_dir / "targets.json").write_text(
        json.dumps({"ts_codes": [], "index_codes": []}),
        encoding="utf-8",
    )
    assert get_default_ts_codes(project_root=tmp_path) == ()
    assert get_runtime_ts_codes(project_root=tmp_path) == ()
    assert get_default_index_codes(project_root=tmp_path) == ()


def test_build_runtime_targets_payload_normalizes_and_deduplicates():
    payload = build_runtime_targets_payload(
        ts_codes=["600519.sh", "000001.SZ", "600519.SH"],
        index_codes=["399300.sz", "000001.SH", "399300.SZ"],
        index_basic_markets=["sw", "csi", "SW"],
        stock_index_basic_categories=["主题指数", "行业指数", "主题指数"],
    )

    assert payload == {
        "ts_codes": ["600519.SH", "000001.SZ"],
        "index_codes": ["399300.SZ", "000001.SH"],
        "index_basic_markets": ["SW", "CSI"],
        "stock_index_basic_categories": ["主题指数", "行业指数"],
    }


def test_write_runtime_targets_supports_function_call_generation(tmp_path):
    output_path = write_runtime_targets(
        ts_codes=["600519.sh", "000001.SZ", "600519.SH"],
        index_codes=["399300.sz", "000001.SH"],
        index_basic_markets=["sse", "szse"],
        stock_index_basic_categories=["规模指数", "行业指数"],
        project_root=tmp_path,
    )

    assert output_path == tmp_path / "runtime" / "targets.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "ts_codes": ["600519.SH", "000001.SZ"],
        "index_codes": ["399300.SZ", "000001.SH"],
        "index_basic_markets": ["SSE", "SZSE"],
        "stock_index_basic_categories": ["规模指数", "行业指数"],
    }


def test_cli_parser_rejects_removed_financial_args():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--income-ts-code", "600000.SH"])


def test_cli_parser_supports_skip_financial_flags():
    args_default = cli.build_parser().parse_args([])
    assert args_default.skip_financial is False

    args_skip = cli.build_parser().parse_args(["--skip-financial"])
    assert args_skip.skip_financial is True


def test_cli_parser_supports_skip_quote_flags():
    args_default = cli.build_parser().parse_args([])
    assert args_default.skip_qfq_daily is False
    assert args_default.skip_qfq_5min is False
    assert args_default.skip_daily_basic is False

    args_skip = cli.build_parser().parse_args(["--skip-qfq-daily", "--skip-qfq-5min"])
    assert args_skip.skip_qfq_daily is True
    assert args_skip.skip_qfq_5min is True

    args_skip_daily_basic = cli.build_parser().parse_args(["--skip-daily-basic"])
    assert args_skip_daily_basic.skip_daily_basic is True
