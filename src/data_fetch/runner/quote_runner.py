from __future__ import annotations

from pathlib import Path

from ..path_manager import (
    build_quote_daily_basic_path,
    build_quote_qfq_5min_path,
    build_quote_qfq_daily_path,
)
from .common import DataFetchError, EmptyDataError, write_csv


def fetch_default_stock_qfq_daily(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    ts_codes: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> None:
    if not ts_codes:
        return
    print("检测到 runtime ts_codes，将按日期范围 " f"{start_date} - {end_date} 获取 A 股前复权日线行情: {', '.join(ts_codes)}")
    for ts_code in ts_codes:
        quote_output_path = build_quote_qfq_daily_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        print(f"正在获取 A 股前复权日线行情: {ts_code} ...")
        try:
            qfq_daily_df = fetcher.fetch_stock_qfq_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            ).data
        except Exception as exc:
            raise DataFetchError(f"A股前复权日线行情获取失败: {exc!r}") from exc
        if qfq_daily_df is None or qfq_daily_df.empty:
            raise EmptyDataError(f"qfq_daily 数据为空（ts_code={ts_code}）")
        write_csv(qfq_daily_df, quote_output_path)
        print(f"- A股前复权日线记录数: {len(qfq_daily_df)}，股票: {ts_code}\n  已保存: {quote_output_path}")


def fetch_default_stock_qfq_5min(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    ts_codes: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> None:
    if not ts_codes:
        return
    print("检测到 runtime ts_codes，将按日期范围 " f"{start_date} - {end_date} 获取 A 股前复权 5min 行情: {', '.join(ts_codes)}")
    for ts_code in ts_codes:
        quote_output_path = build_quote_qfq_5min_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        print(f"正在获取 A 股前复权 5min 行情: {ts_code} ...")
        try:
            qfq_5min_df = fetcher.fetch_stock_qfq_5min(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            ).data
        except Exception as exc:
            raise DataFetchError(f"A股前复权5min行情获取失败: {exc!r}") from exc
        if qfq_5min_df is None or qfq_5min_df.empty:
            raise EmptyDataError(f"qfq_5min 数据为空（ts_code={ts_code}）")
        write_csv(qfq_5min_df, quote_output_path)
        print(f"- A股前复权5min记录数: {len(qfq_5min_df)}，股票: {ts_code}\n  已保存: {quote_output_path}")


def fetch_default_stock_daily_basic(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    ts_codes: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> None:
    if not ts_codes:
        return
    print("检测到 runtime ts_codes，将按日期范围 " f"{start_date} - {end_date} 获取每日指标 daily_basic: {', '.join(ts_codes)}")
    for ts_code in ts_codes:
        quote_output_path = build_quote_daily_basic_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        print(f"正在获取每日指标 daily_basic: {ts_code} ...")
        try:
            daily_basic_df = fetcher.fetch_stock_daily_basic(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            ).data
        except Exception as exc:
            raise DataFetchError(f"daily_basic 获取失败: {exc!r}") from exc
        if daily_basic_df is None or daily_basic_df.empty:
            raise EmptyDataError(f"daily_basic 数据为空（ts_code={ts_code}）")
        write_csv(daily_basic_df, quote_output_path)
        print(f"- daily_basic 记录数: {len(daily_basic_df)}，股票: {ts_code}\n  已保存: {quote_output_path}")
