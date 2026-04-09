"""
股票相关数据获取
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty


# 中证全指指数代码
CSI_ALL_SHARE_INDEX = "000985.CSI"


def fetch_stock_list(output_dir: Path, today_ymd: str) -> None:
    """获取股票列表（通过中证全指 000985.CSI 成分股）"""
    pro = get_tushare_pro()
    
    path = output_dir / today_ymd / "stock" / "stock_list" / "stock_list.csv"
    if file_exists_and_not_empty(path):
        print(f"已存在，跳过: {path}")
        return
    
    print(f"正在获取股票列表（通过中证全指 {CSI_ALL_SHARE_INDEX} 成分股）...")
    df = pro.index_weight(index_code=CSI_ALL_SHARE_INDEX)
    if df is None or df.empty:
        print(f"警告: 无法获取 {CSI_ALL_SHARE_INDEX} 成分股数据")
        return
    
    # 去重，保留最新的
    df = df.sort_values("trade_date", ascending=False).drop_duplicates("con_code", keep="first")
    
    # 重命名列为标准格式
    df = df.rename(columns={
        "con_code": "ts_code",
        "trade_date": "in_date",
    })
    
    save_csv(df, path)
    print(f"- 股票列表: {len(df)} 条")


def get_all_stock_codes(data_dir: Path | None = None, today_ymd: str | None = None) -> list[str]:
    """
    获取中证全指成分股股票代码
    
    优先从已保存的股票列表文件读取，否则实时获取
    
    Args:
        data_dir: 数据目录，如果提供则优先从文件读取
        today_ymd: 日期目录，配合 data_dir 使用
    
    Returns:
        股票代码列表
    """
    # 尝试从文件读取
    if data_dir and today_ymd:
        stock_list_path = data_dir / today_ymd / "stock" / "stock_list" / "stock_list.csv"
        if stock_list_path.exists():
            try:
                df = pd.read_csv(stock_list_path, encoding="utf-8")
                if "ts_code" in df.columns:
                    codes = df["ts_code"].astype(str).tolist()
                    print(f"从文件读取股票列表: {len(codes)} 只")
                    return codes
            except Exception:
                pass
    
    # 实时获取
    pro = get_tushare_pro()
    print("正在实时获取中证全指成分股...")
    
    df = pro.index_weight(index_code=CSI_ALL_SHARE_INDEX)
    if df is None or df.empty:
        print(f"警告: 无法获取 {CSI_ALL_SHARE_INDEX} 成分股")
        return []
    
    # 去重，保留最新的
    df = df.sort_values("trade_date", ascending=False).drop_duplicates("con_code", keep="first")
    codes = df["con_code"].astype(str).tolist()
    
    print(f"- 获取到 {len(codes)} 只股票代码")
    return codes


def fetch_stock_st(output_dir: Path, today_ymd: str) -> None:
    """获取 ST 股票列表"""
    pro = get_tushare_pro()
    path = output_dir / today_ymd / "stock" / "st_stock_list" / "st_stock_list.csv"

    if file_exists_and_not_empty(path):
        print(f"已存在，跳过: {path}")
        return

    print("正在获取 ST 股票列表...")
    df = pro.stock_st(trade_date=today_ymd)
    save_csv(df, path)
    print(f"- ST 股票列表: {len(df)} 条")
