"""
股票相关数据获取
"""

from __future__ import annotations

from pathlib import Path

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty


def fetch_stock_list(output_dir: Path, today_ymd: str) -> None:
    """获取所有股票列表（上交所 + 深交所）"""
    pro = get_tushare_pro()

    # 上交所
    sh_path = output_dir / today_ymd / "stock" / "stock_list" / f"stock_list_sh_{today_ymd}.csv"
    if file_exists_and_not_empty(sh_path):
        print(f"已存在，跳过: {sh_path}")
    else:
        print("正在获取上交所股票列表...")
        sh_df = pro.query("stock_basic", exchange="SSE", list_status="L", market="主板")
        save_csv(sh_df, sh_path)
        print(f"- 上交所股票列表: {len(sh_df)} 条")

    # 深交所
    sz_path = output_dir / today_ymd / "stock" / "stock_list" / f"stock_list_sz_{today_ymd}.csv"
    if file_exists_and_not_empty(sz_path):
        print(f"已存在，跳过: {sz_path}")
    else:
        print("正在获取深交所股票列表...")
        sz_df = pro.query("stock_basic", exchange="SZSE", list_status="L", market="主板")
        save_csv(sz_df, sz_path)
        print(f"- 深交所股票列表: {len(sz_df)} 条")


def get_all_stock_codes() -> list[str]:
    """实时获取所有主板股票代码"""
    pro = get_tushare_pro()
    print("正在实时获取股票代码列表...")

    # 上交所主板
    sh_df = pro.query("stock_basic", exchange="SSE", list_status="L", market="主板")
    sh_codes = sh_df["ts_code"].tolist() if "ts_code" in sh_df.columns else []

    # 深交所主板
    sz_df = pro.query("stock_basic", exchange="SZSE", list_status="L", market="主板")
    sz_codes = sz_df["ts_code"].tolist() if "ts_code" in sz_df.columns else []

    all_codes = sh_codes + sz_codes
    print(f"- 获取到 {len(all_codes)} 只股票代码")
    return all_codes


def fetch_stock_hsgt(output_dir: Path, today_ymd: str, start_date: str) -> None:
    """获取沪深港通股票列表"""
    pro = get_tushare_pro()
    path = output_dir / today_ymd / "stock" / "hsgt_stock_list" / f"hsgt_stock_list_{start_date}_{today_ymd}.csv"

    if file_exists_and_not_empty(path):
        print(f"已存在，跳过: {path}")
        return

    print("正在获取沪深港通股票列表...")
    df = pro.query("hs_const", ts_code="", is_new="1")
    save_csv(df, path)
    print(f"- 沪深港通股票列表: {len(df)} 条")


def fetch_stock_st(output_dir: Path, today_ymd: str) -> None:
    """获取 ST 股票列表"""
    pro = get_tushare_pro()
    path = output_dir / today_ymd / "stock" / "st_stock_list" / f"st_stock_list_{today_ymd}.csv"

    if file_exists_and_not_empty(path):
        print(f"已存在，跳过: {path}")
        return

    print("正在获取 ST 股票列表...")
    df = pro.query("stk_limit", trade_date=today_ymd)
    save_csv(df, path)
    print(f"- ST 股票列表: {len(df)} 条")
