"""
公司相关数据获取
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from tqdm import tqdm

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty

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


def _fetch_single_company(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
    pro,
) -> tuple[str, bool]:
    """获取单只股票的公司基本信息"""
    path = output_dir / today_ymd / "company" / f"{ts_code.replace('.', '_')}.csv"

    try:
        df = _rate_limited_api_call(pro.stock_company, ts_code=ts_code)
        if df is None or df.empty:
            return ts_code, False
        save_csv(df, path)
        return ts_code, True
    except Exception:
        return ts_code, False


def fetch_company_basic_info(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    max_workers: int = 8,
) -> None:
    """获取公司基本信息（指定股票列表）"""
    if not ts_codes:
        return

    pro = get_tushare_pro()

    # 批量读取已存在的文件
    target_dir = output_dir / today_ymd / "company"
    existing_codes = _get_existing_codes_from_dir(target_dir)
    
    # 过滤出需要下载的股票
    ts_codes_set = set(ts_codes)
    existing = ts_codes_set & existing_codes
    to_download = list(ts_codes_set - existing_codes)

    if not to_download:
        print(f"公司基本信息: 全部 {len(ts_codes)} 只已存在，跳过")
        return

    print(f"公司基本信息: 共 {len(ts_codes)} 只，{len(existing)} 只已存在，需下载 {len(to_download)} 只")

    with tqdm(total=len(ts_codes), desc="公司信息", initial=len(existing)) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_single_company,
                    ts_code,
                    output_dir,
                    today_ymd,
                    pro,
                ): ts_code
                for ts_code in to_download
            }
            for future in as_completed(futures):
                future.result()
                pbar.update(1)


def _check_all_financial_exist(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
) -> bool:
    """检查某只股票的三张表是否都已存在"""
    code_filename = ts_code.replace('.', '_')
    
    bs_path = output_dir / today_ymd / "financial" / "balancesheet" / f"{code_filename}.csv"
    inc_path = output_dir / today_ymd / "financial" / "income" / f"{code_filename}.csv"
    cf_path = output_dir / today_ymd / "financial" / "cashflow" / f"{code_filename}.csv"
    
    return (
        file_exists_and_not_empty(bs_path)
        and file_exists_and_not_empty(inc_path)
        and file_exists_and_not_empty(cf_path)
    )


def _fetch_single_financial(
    ts_code: str,
    output_dir: Path,
    today_ymd: str,
    start_date: str,
    end_date: str,
    pro,
) -> tuple[str, int]:
    """获取单只股票的财务报表，返回 (ts_code, 下载文件数)"""
    count = 0
    code_filename = ts_code.replace('.', '_')

    # 资产负债表
    bs_path = output_dir / today_ymd / "financial" / "balancesheet" / f"{code_filename}.csv"
    if not file_exists_and_not_empty(bs_path):
        try:
            df = _rate_limited_api_call(
                pro.balancesheet,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                save_csv(df, bs_path)
                count += 1
        except Exception:
            pass

    # 利润表
    inc_path = output_dir / today_ymd / "financial" / "income" / f"{code_filename}.csv"
    if not file_exists_and_not_empty(inc_path):
        try:
            df = _rate_limited_api_call(
                pro.income,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                save_csv(df, inc_path)
                count += 1
        except Exception:
            pass

    # 现金流量表
    cf_path = output_dir / today_ymd / "financial" / "cashflow" / f"{code_filename}.csv"
    if not file_exists_and_not_empty(cf_path):
        try:
            df = _rate_limited_api_call(
                pro.cashflow,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                save_csv(df, cf_path)
                count += 1
        except Exception:
            pass

    return ts_code, count


def fetch_financial_statements(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
    max_workers: int = 8,
) -> None:
    """获取财务报表（并发）"""
    if not ts_codes:
        return

    pro = get_tushare_pro()

    # 从 financial/balancesheet 目录读取已存在的代码作为参考
    target_dir = output_dir / today_ymd / "financial" / "balancesheet"
    existing_codes = _get_existing_codes_from_dir(target_dir)
    
    # 检查完整存在的（三张表都有）
    ts_codes_set = set(ts_codes)
    fully_existing = {code for code in ts_codes_set if code in existing_codes and _check_all_financial_exist(code, output_dir, today_ymd)}
    to_download = list(ts_codes_set - fully_existing)

    if not to_download:
        print(f"财务报表: 全部 {len(ts_codes)} 只已存在，跳过")
        return

    print(f"财务报表: 共 {len(ts_codes)} 只，{len(fully_existing)} 只已存在，需处理 {len(to_download)} 只")

    with tqdm(total=len(ts_codes), desc="财务报表", initial=len(fully_existing)) as pbar:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _fetch_single_financial,
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
