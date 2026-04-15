"""
股票相关数据获取
"""

from __future__ import annotations

from pathlib import Path

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
