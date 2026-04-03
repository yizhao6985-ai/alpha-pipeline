"""
行情数据获取
"""

from __future__ import annotations

from pathlib import Path

from .base import get_tushare_pro, get_required_env, save_csv, file_exists_and_not_empty


def fetch_qfq_daily(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
) -> None:
    """获取前复权日线行情"""
    if not ts_codes:
        return

    import tushare as ts

    print(f"正在获取 {len(ts_codes)} 只股票的日线行情...")

    for ts_code in ts_codes:
        path = (
            output_dir
            / today_ymd
            / "quote"
            / "qfq_daily"
            / f"qfq_daily_{ts_code.replace('.', '_')}_{start_date}_{end_date}.csv"
        )
        if file_exists_and_not_empty(path):
            print(f"  已存在，跳过 {ts_code}")
            continue

        # 使用 ts.pro_bar 获取前复权日线
        ts.set_token(get_required_env("TUSHARE_TOKEN"))
        df = ts.pro_bar(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            asset="E",
            adj="qfq",
            freq="D",
            adjfactor=True,
        )
        if df is None or df.empty:
            print(f"  警告: {ts_code} 无数据")
            continue
        save_csv(df, path)
        print(f"- {ts_code}: {len(df)} 条")


def fetch_daily_basic(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
) -> None:
    """获取每日指标"""
    if not ts_codes:
        return

    pro = get_tushare_pro()
    print(f"正在获取 {len(ts_codes)} 只股票的每日指标...")

    for ts_code in ts_codes:
        path = (
            output_dir
            / today_ymd
            / "quote"
            / "daily_basic"
            / f"daily_basic_{ts_code.replace('.', '_')}_{start_date}_{end_date}.csv"
        )
        if file_exists_and_not_empty(path):
            print(f"  已存在，跳过 {ts_code}")
            continue

        df = pro.daily_basic(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            print(f"  警告: {ts_code} 无数据")
            continue
        save_csv(df, path)
        print(f"- {ts_code}: {len(df)} 条")


def fetch_adj_factor(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
) -> None:
    """获取复权因子"""
    if not ts_codes:
        return

    pro = get_tushare_pro()
    print(f"正在获取 {len(ts_codes)} 只股票的复权因子...")

    for ts_code in ts_codes:
        path = (
            output_dir
            / today_ymd
            / "quote"
            / "adj_factor"
            / f"adj_factor_{ts_code.replace('.', '_')}_{start_date}_{end_date}.csv"
        )
        if file_exists_and_not_empty(path):
            print(f"  已存在，跳过 {ts_code}")
            continue

        df = pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            print(f"  警告: {ts_code} 无数据")
            continue
        save_csv(df, path)
        print(f"- {ts_code}: {len(df)} 条")
