"""
指数相关数据获取
"""

from __future__ import annotations

import time
from pathlib import Path
from threading import Lock

from .base import (
    get_tushare_pro,
    retry_if_triplet_api_error,
    run_parallel_with_rate_limit_retries,
    save_csv,
    file_exists_and_not_empty,
    triplet_indicates_success,
)

# Tushare API 限流控制
_MIN_API_INTERVAL = 0.05  # 最小请求间隔（秒），约 20 QPS
_api_lock = Lock()
_last_api_time = 0.0


def _rate_limited_api_call(api_func, *args, **kwargs):
    """带速率限制的 API 调用"""
    global _last_api_time
    with _api_lock:
        elapsed = time.time() - _last_api_time
        if elapsed < _MIN_API_INTERVAL:
            time.sleep(_MIN_API_INTERVAL - elapsed)
        _last_api_time = time.time()
    return api_func(*args, **kwargs)


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
            path = output_dir / today_ymd / "index" / "index_basic" / market / f"index_basic_{market}_{category}.csv"
            if file_exists_and_not_empty(path):
                print(f"  已存在，跳过 {market}/{category}")
                continue
            save_csv(category_df.reset_index(drop=True), path)
            print(f"- {market}/{category}: {len(category_df)} 条")


def _get_existing_index_codes_from_dir(directory: Path) -> set[str]:
    """从目录中读取已存在的指数代码"""
    if not directory.exists():
        return set()
    
    existing = set()
    suffix = ".csv"
    
    for f in directory.iterdir():
        if f.is_file() and f.name.endswith(suffix):
            # 提取指数代码: 399300_SZ.csv -> 399300.SZ
            name = f.name[:-len(suffix)]  # 399300_SZ
            if "_" in name:
                parts = name.rsplit("_", 1)
                if len(parts) == 2:
                    code, exchange = parts
                    existing.add(f"{code}.{exchange}")
    
    return existing


def _fetch_single_index_weight(
    index_code: str,
    output_dir: Path,
    today_ymd: str,
    pro,
) -> tuple[str, bool, int]:
    """获取单个指数的成分和权重"""
    path = output_dir / today_ymd / "index" / "index_weight" / f"{index_code.replace('.', '_')}.csv"

    try:
        df = _rate_limited_api_call(pro.index_weight, index_code=index_code)
        if df is None or df.empty:
            return index_code, False, 0
        # 取最新交易日数据
        latest_date = df["trade_date"].max()
        latest_df = df[df["trade_date"] == latest_date].reset_index(drop=True)
        save_csv(latest_df, path)
        return index_code, True, len(latest_df)
    except Exception:
        return index_code, False, -1


def fetch_index_weight(
    output_dir: Path,
    today_ymd: str,
    index_codes: list[str],
    max_workers: int = 4,
) -> None:
    """获取指数成分和权重（并发）"""
    if not index_codes:
        return

    pro = get_tushare_pro()

    target_dir = output_dir / today_ymd / "index" / "index_weight"
    existing_codes = _get_existing_index_codes_from_dir(target_dir)
    
    index_codes_set = set(index_codes)
    existing = index_codes_set & existing_codes
    to_download = list(index_codes_set - existing_codes)

    if not to_download:
        print(f"指数权重: 全部 {len(index_codes)} 个指数已存在，跳过")
        return

    print(f"指数权重: 共 {len(index_codes)} 个，{len(existing)} 个已存在，需下载 {len(to_download)} 个")

    def _work(code: str) -> tuple[str, bool, int]:
        return _fetch_single_index_weight(code, output_dir, today_ymd, pro)

    run_parallel_with_rate_limit_retries(
        to_download,
        max_workers,
        _work,
        retry_if_triplet_api_error,
        triplet_indicates_success,
        "指数权重",
        "个",
    )


def _fetch_single_index_daily(
    index_code: str,
    output_dir: Path,
    today_ymd: str,
    start_date: str,
    end_date: str,
    pro,
) -> tuple[str, bool, int]:
    """获取单个指数的日线行情"""
    path = output_dir / today_ymd / "index" / "index_daily" / f"{index_code.replace('.', '_')}.csv"
    
    if file_exists_and_not_empty(path):
        return index_code, True, 0  # 已存在
    
    try:
        df = _rate_limited_api_call(
            pro.index_daily, 
            ts_code=index_code,
            start_date=start_date,
            end_date=end_date
        )
        if df is None or df.empty:
            return index_code, False, 0
        save_csv(df, path)
        return index_code, True, len(df)
    except Exception as e:
        return index_code, False, -1


def fetch_index_daily(
    output_dir: Path,
    today_ymd: str,
    index_codes: list[str],
    start_date: str,
    end_date: str,
    max_workers: int = 4,
) -> None:
    """获取指数日线行情（并发）
    
    根据 Tushare 文档，index_daily 返回字段：
    - ts_code: 指数代码
    - trade_date: 交易日期
    - close: 收盘点位
    - open: 开盘点位
    - high: 最高点位
    - low: 最低点位
    - pre_close: 昨日收盘点
    - change: 涨跌点
    - pct_chg: 涨跌幅(%)
    - vol: 成交量（手）
    - amount: 成交额（千元）
    """
    if not index_codes:
        return
    
    pro = get_tushare_pro()
    
    target_dir = output_dir / today_ymd / "index" / "index_daily"
    existing_codes = _get_existing_index_codes_from_dir(target_dir)
    
    index_codes_set = set(index_codes)
    existing = index_codes_set & existing_codes
    to_download = list(index_codes_set - existing_codes)
    
    if not to_download:
        print(f"指数行情: 全部 {len(index_codes)} 个指数已存在，跳过")
        return
    
    print(f"指数行情: 共 {len(index_codes)} 个，{len(existing)} 个已存在，需下载 {len(to_download)} 个")

    def _work(code: str) -> tuple[str, bool, int]:
        return _fetch_single_index_daily(
            code, output_dir, today_ymd, start_date, end_date, pro
        )

    run_parallel_with_rate_limit_retries(
        to_download,
        max_workers,
        _work,
        retry_if_triplet_api_error,
        triplet_indicates_success,
        "指数行情",
        "个",
    )
