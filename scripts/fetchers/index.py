"""
指数相关数据获取
"""

from __future__ import annotations

from pathlib import Path

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty


def fetch_index_basic(output_dir: Path, today_ymd: str) -> None:
    """获取股票类指数基础信息"""
    pro = get_tushare_pro()
    markets = ["CSI", "SSE", "SZSE"]

    print("正在获取股票类指数基础信息...")
    df = pro.query("index_basic", market="")
    # 过滤股票类指数
    stock_index_df = df[df["category"].isin(["主题指数", "规模指数", "策略指数", "风格指数", "综合指数", "行业指数"])]

    for market in markets:
        market_df = stock_index_df[stock_index_df["market"] == market]
        for category, category_df in market_df.groupby("category"):
            path = output_dir / today_ymd / "index" / "index_basic" / market / f"index_basic_{market}_{category}_{today_ymd}.csv"
            if file_exists_and_not_empty(path):
                print(f"  已存在，跳过 {market}/{category}")
                continue
            save_csv(category_df.reset_index(drop=True), path)
            print(f"- {market}/{category}: {len(category_df)} 条")


def fetch_index_weight(output_dir: Path, today_ymd: str, index_codes: list[str]) -> None:
    """获取指数成分和权重"""
    if not index_codes:
        return

    pro = get_tushare_pro()
    print(f"正在获取指数成分和权重: {', '.join(index_codes)}")

    for index_code in index_codes:
        path = output_dir / today_ymd / "index" / "index_weight" / f"index_weight_{index_code.replace('.', '_')}_{today_ymd}.csv"
        if file_exists_and_not_empty(path):
            print(f"  已存在，跳过 {index_code}")
            continue

        df = pro.index_weight(index_code=index_code)
        if df is None or df.empty:
            print(f"  警告: {index_code} 无数据")
            continue
        # 取最新交易日数据
        latest_date = df["trade_date"].max()
        latest_df = df[df["trade_date"] == latest_date].reset_index(drop=True)
        save_csv(latest_df, path)
        print(f"- {index_code}: {len(latest_df)} 条 (日期: {latest_date})")
