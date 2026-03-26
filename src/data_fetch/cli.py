import argparse
from pathlib import Path

from .config import get_required_env
from .fetcher import build_default_fetcher
from .parser import build_parser
from .runner import (
    DataFetchError,
    fetch_company_basic_info,
    fetch_default_stock_daily_basic,
    fetch_default_financial_statements,
    fetch_default_index_weights,
    fetch_default_stock_qfq_5min,
    fetch_default_stock_qfq_daily,
    fetch_stock_base_datasets,
    fetch_stock_index_basic,
    fetch_trade_calendar,
)
from .runtime import ensure_runtime_dir, get_default_index_basic_markets, get_default_index_codes, get_runtime_ts_codes
from .utils import reset_today_output_dir


def _resolve_runtime_defaults() -> tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    from .config import get_default_fetch_end_date, get_default_fetch_start_date

    today_ymd = get_default_fetch_end_date()
    default_start_date = get_default_fetch_start_date()
    default_index_codes = get_default_index_codes()
    index_basic_markets = get_default_index_basic_markets()
    default_ts_codes = get_runtime_ts_codes()
    return (
        today_ymd,
        default_start_date,
        default_index_codes,
        index_basic_markets,
        default_ts_codes,
    )


def run(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    ensure_runtime_dir()

    try:
        import tushare  # noqa: F401
        get_required_env("TUSHARE_TOKEN")
    except ModuleNotFoundError as exc:
        raise SystemExit("未检测到 tushare，请先安装: pip install -r requirements.txt") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        run_inner(args)
    except DataFetchError as exc:
        print(f"数据获取失败: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"发生未预期错误: {exc!r}")
        raise SystemExit(2) from exc


def run_inner(args: argparse.Namespace) -> None:
    output_dir = Path(args.output_dir)
    ensure_runtime_dir()
    (
        today_ymd,
        default_start_date,
        default_index_codes,
        index_basic_markets,
        default_ts_codes,
    ) = _resolve_runtime_defaults()
    reset_today_output_dir(
        output_dir=output_dir,
        today_ymd=today_ymd,
        has_index_weights=bool(default_index_codes),
        has_ts_codes=bool(default_ts_codes),
        skip_financial=args.skip_financial,
        skip_qfq_daily=args.skip_qfq_daily,
        skip_qfq_5min=args.skip_qfq_5min,
        skip_daily_basic=args.skip_daily_basic,
    )
    fetcher = build_default_fetcher()

    fetch_stock_index_basic(
        output_dir=output_dir,
        today_ymd=today_ymd,
        fetcher=fetcher,
        index_basic_markets=index_basic_markets,
    )
    fetch_default_index_weights(
        output_dir=output_dir,
        today_ymd=today_ymd,
        fetcher=fetcher,
        index_codes=default_index_codes,
    )
    fetch_stock_base_datasets(
        output_dir=output_dir,
        today_ymd=today_ymd,
        fetcher=fetcher,
        start_date=default_start_date,
    )
    if args.skip_qfq_daily:
        print("检测到 --skip-qfq-daily，已跳过A股前复权日线行情抓取")
    else:
        fetch_default_stock_qfq_daily(
            output_dir=output_dir,
            today_ymd=today_ymd,
            fetcher=fetcher,
            ts_codes=default_ts_codes,
            start_date=default_start_date,
            end_date=today_ymd,
        )
    # 上游 API 受限，qfq_5min 暂时停用。
    # if args.skip_qfq_5min:
    #     print("检测到 --skip-qfq-5min，已跳过A股前复权5分钟行情抓取")
    # else:
    #     fetch_default_stock_qfq_5min(
    #         output_dir=output_dir,
    #         today_ymd=today_ymd,
    #         fetcher=fetcher,
    #         ts_codes=default_ts_codes,
    #         start_date=default_start_date,
    #         end_date=today_ymd,
    #     )
    print("A股前复权5分钟行情抓取已暂时停用（上游API调用限制）")
    if args.skip_daily_basic:
        print("检测到 --skip-daily-basic，已跳过A股每日指标（daily_basic）抓取")
    else:
        fetch_default_stock_daily_basic(
            output_dir=output_dir,
            today_ymd=today_ymd,
            fetcher=fetcher,
            ts_codes=default_ts_codes,
            start_date=default_start_date,
            end_date=today_ymd,
        )

    fetch_company_basic_info(output_dir=output_dir, today_ymd=today_ymd, fetcher=fetcher)

    if args.skip_financial:
        print("检测到 --skip-financial，已跳过公司财报抓取")
    else:
        fetch_default_financial_statements(
            output_dir=output_dir,
            today_ymd=today_ymd,
            fetcher=fetcher,
            ts_codes=default_ts_codes,
            start_date=default_start_date,
            end_date=today_ymd,
        )

    fetch_trade_calendar(
        output_dir=output_dir,
        today_ymd=today_ymd,
        fetcher=fetcher,
        start_date=default_start_date,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run(args)

