from __future__ import annotations

from pathlib import Path

from ..path_manager import build_trade_calendar_path, has_current_data
from .common import DataFetchError, EmptyDataError, write_csv


def fetch_trade_calendar(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    start_date: str,
) -> None:
    trade_calendar_path = build_trade_calendar_path(
        base_dir=output_dir,
        today_ymd=today_ymd,
        start_date=start_date,
        end_date=today_ymd,
    )
    if has_current_data(trade_calendar_path):
        print(f"已存在，跳过交易日历数据: {trade_calendar_path}")
        return
    print("正在获取交易日历数据...")
    try:
        trade_calendar_df = fetcher.fetch_trade_calendar(update_date=today_ymd).data
    except Exception as exc:
        raise DataFetchError(f"交易日历数据获取失败: {exc!r}") from exc
    if trade_calendar_df is None or trade_calendar_df.empty:
        raise EmptyDataError(f"trade_calendar 数据为空（update_date={today_ymd}）")
    write_csv(trade_calendar_df, trade_calendar_path)
    print(f"- 交易日历记录数: {len(trade_calendar_df)}，更新日期: {today_ymd}\n  已保存: {trade_calendar_path}")
