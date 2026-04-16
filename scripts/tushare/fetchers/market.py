"""
市场相关数据获取
"""

from __future__ import annotations

from pathlib import Path

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty


def fetch_trade_calendar(output_dir: Path, today_ymd: str, start_date: str) -> None:
    """获取交易日历"""
    pro = get_tushare_pro()
    path = output_dir / today_ymd / "calendar" / "trade_calendar.csv"

    if file_exists_and_not_empty(path):
        print(f"已存在，跳过: {path}")
        return

    print("正在获取交易日历...")
    df = pro.query("trade_cal", start_date=start_date, end_date=today_ymd)
    save_csv(df, path)
    print(f"- 交易日历: {len(df)} 条")
