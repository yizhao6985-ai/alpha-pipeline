"""
行情数据获取
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from tqdm import tqdm

from .base import get_tushare_pro, get_required_env, save_csv, file_exists_and_not_empty

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


def _get_existing_codes_from_dir(directory: Path) -> set[str]:
    """从目录中读取已存在的股票代码"""
    if not directory.exists():
        return set()
    
    existing = set()
    suffix = ".csv"
    
    for f in directory.iterdir():
        if f.is_file() and f.name.endswith(suffix):
            # 提取股票代码: 600000_SH.csv -> 600000.SH
            name = f.name[:-len(suffix)]  # 600000_SH
            if "_" in name:
                parts = name.rsplit("_", 1)
                if len(parts) == 2:
                    code, exchange = parts
                    existing.add(f"{code}.{exchange}")
    
    return existing


def _fetch_single_qfq_daily(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
    start_date: str,
    end_date: str,
    token: str,
) -> tuple[str, bool, int]:
    """获取单只股票的日线行情"""
    import tushare as ts

    path = output_dir / today_ymd / "quote" / "qfq" / f"{ts_code.replace('.', '_')}.csv"

    try:
        ts.set_token(token)
        df = _rate_limited_api_call(
            ts.pro_bar,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            asset="E",
            adj="qfq",
            freq="D",
            adjfactor=True,
        )
        if df is None or df.empty:
            return ts_code, False, 0  # 无数据
        save_csv(df, path)
        return ts_code, True, len(df)
    except Exception:
        return ts_code, False, -1  # 错误


def fetch_qfq_daily(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
    max_workers: int = 8,
) -> None:
    """获取前复权日线行情（并发）"""
    if not ts_codes:
        return

    token = get_required_env("TUSHARE_TOKEN")
    
    # 批量读取已存在的文件
    target_dir = output_dir / today_ymd / "quote" / "qfq"
    existing_codes = _get_existing_codes_from_dir(target_dir)
    
    # 过滤出需要下载的股票
    ts_codes_set = set(ts_codes)
    existing = ts_codes_set & existing_codes
    to_download = list(ts_codes_set - existing_codes)

    if not to_download:
        print(f"日线行情: 全部 {len(ts_codes)} 只股票已存在，跳过")
        return

    print(f"日线行情: 共 {len(ts_codes)} 只，{len(existing)} 只已存在，需下载 {len(to_download)} 只")

    with tqdm(total=len(ts_codes), desc="日线行情", initial=len(existing)) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_single_qfq_daily,
                    ts_code,
                    output_dir,
                    today_ymd,
                    start_date,
                    end_date,
                    token,
                ): ts_code
                for ts_code in to_download
            }
            for future in as_completed(futures):
                future.result()
                pbar.update(1)


def _fetch_single_daily_basic(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
    start_date: str,
    end_date: str,
    pro,
) -> tuple[str, bool, int]:
    """获取单只股票的每日指标"""
    path = output_dir / today_ymd / "quote" / "basic" / f"{ts_code.replace('.', '_')}.csv"

    try:
        df = _rate_limited_api_call(
            pro.daily_basic,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if df is None or df.empty:
            return ts_code, False, 0
        save_csv(df, path)
        return ts_code, True, len(df)
    except Exception:
        return ts_code, False, -1


def fetch_daily_basic(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
    max_workers: int = 8,
) -> None:
    """获取每日指标（并发）"""
    if not ts_codes:
        return

    pro = get_tushare_pro()

    target_dir = output_dir / today_ymd / "quote" / "basic"
    existing_codes = _get_existing_codes_from_dir(target_dir)
    
    ts_codes_set = set(ts_codes)
    existing = ts_codes_set & existing_codes
    to_download = list(ts_codes_set - existing_codes)

    if not to_download:
        print(f"每日指标: 全部 {len(ts_codes)} 只股票已存在，跳过")
        return

    print(f"每日指标: 共 {len(ts_codes)} 只，{len(existing)} 只已存在，需下载 {len(to_download)} 只")

    with tqdm(total=len(ts_codes), desc="每日指标", initial=len(existing)) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_single_daily_basic,
                    ts_code,
                    output_dir,
                    today_ymd,
                    start_date,
                    end_date,
                    pro,
                ): ts_code
                for ts_code in to_download
            }
            for future in as_completed(futures):
                future.result()
                pbar.update(1)


def _fetch_single_cyq_perf(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
    start_date: str,
    end_date: str,
    pro,
    max_retries: int = 3,
) -> tuple[str, bool, int]:
    """获取单只股票的每日筹码及胜率（该接口限流 800/分钟，需要更慢的速率）"""
    path = output_dir / today_ymd / "quote" / "cyq" / f"{ts_code.replace('.', '_')}.csv"

    for attempt in range(max_retries):
        try:
            # cyq_perf 接口限流 800/分钟，使用 0.1 秒间隔（约 600 QPS，留有余量）
            global _last_api_time
            with _api_lock:
                elapsed = time.time() - _last_api_time
                if elapsed < 0.1:
                    time.sleep(0.1 - elapsed)
                _last_api_time = time.time()
            
            df = pro.cyq_perf(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is None or df.empty:
                return ts_code, False, 0
            save_csv(df, path)
            return ts_code, True, len(df)
        except Exception as e:
            if attempt < max_retries - 1:
                # 指数退避重试
                time.sleep(0.5 * (2 ** attempt))
                continue
            # 最终失败
            return ts_code, False, -1


def fetch_cyq_perf(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
    max_workers: int = 4,  # cyq_perf 接口限流严格，减少并发数
) -> list[str]:
    """获取每日筹码及胜率（并发）
    
    返回:
        下载失败的股票代码列表
    """
    if not ts_codes:
        return []

    pro = get_tushare_pro()

    target_dir = output_dir / today_ymd / "quote" / "cyq"
    existing_codes = _get_existing_codes_from_dir(target_dir)
    
    ts_codes_set = set(ts_codes)
    existing = ts_codes_set & existing_codes
    to_download = list(ts_codes_set - existing_codes)

    if not to_download:
        print(f"筹码胜率: 全部 {len(ts_codes)} 只股票已存在，跳过")
        return []

    print(f"筹码胜率: 共 {len(ts_codes)} 只，{len(existing)} 只已存在，需下载 {len(to_download)} 只")

    failed_codes = []
    success_count = 0
    
    with tqdm(total=len(to_download), desc="筹码胜率") as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_single_cyq_perf,
                    ts_code,
                    output_dir,
                    today_ymd,
                    start_date,
                    end_date,
                    pro,
                ): ts_code
                for ts_code in to_download
            }
            for future in as_completed(futures):
                ts_code, success, count = future.result()
                if success:
                    success_count += 1
                else:
                    failed_codes.append(ts_code)
                pbar.update(1)
                pbar.set_postfix({"成功": success_count, "失败": len(failed_codes)})
    
    print(f"筹码胜率下载完成: 成功 {success_count} 只，失败 {len(failed_codes)} 只")
    return failed_codes


def _fetch_single_adj_factor(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
    start_date: str,
    end_date: str,
    pro,
) -> tuple[str, bool, int]:
    """获取单只股票的复权因子"""
    path = (
        output_dir
        / today_ymd
        / "quote"
        / "adj_factor"
        / f"{ts_code.replace('.', '_')}.csv"
    )

    try:
        df = _rate_limited_api_call(
            pro.adj_factor,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if df is None or df.empty:
            return ts_code, False, 0
        save_csv(df, path)
        return ts_code, True, len(df)
    except Exception:
        return ts_code, False, -1


def fetch_adj_factor(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
    max_workers: int = 8,
) -> None:
    """获取复权因子（并发）"""
    if not ts_codes:
        return

    pro = get_tushare_pro()

    target_dir = output_dir / today_ymd / "quote" / "adj_factor"
    existing_codes = _get_existing_codes_from_dir(target_dir)
    
    ts_codes_set = set(ts_codes)
    existing = ts_codes_set & existing_codes
    to_download = list(ts_codes_set - existing_codes)

    if not to_download:
        print(f"复权因子: 全部 {len(ts_codes)} 只股票已存在，跳过")
        return

    print(f"复权因子: 共 {len(ts_codes)} 只，{len(existing)} 只已存在，需下载 {len(to_download)} 只")

    with tqdm(total=len(ts_codes), desc="复权因子", initial=len(existing)) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_single_adj_factor,
                    ts_code,
                    output_dir,
                    today_ymd,
                    start_date,
                    end_date,
                    pro,
                ): ts_code
                for ts_code in to_download
            }
            for future in as_completed(futures):
                future.result()
                pbar.update(1)
