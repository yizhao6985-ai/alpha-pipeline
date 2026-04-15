"""
基础工具函数
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TypeVar

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

TUSHARE_RATE_LIMIT_RETRY_SLEEP_SEC = 20.0

T = TypeVar("T")


def run_parallel_with_rate_limit_retries(
    items: list[T],
    max_workers: int,
    fetch_fn: Callable[[T], object],
    should_retry: Callable[[T, object], bool],
    is_success: Callable[[T, object], bool],
    desc: str,
    unit: str = "",
) -> list[T]:
    """并发执行 fetch_fn；对 should_retry 为 True 的任务在整轮结束后 sleep 再重试。

    进度条仅在任务最终不再重试时前进（成功或永久失败各计 1）。

    返回：永久失败（不再重试且 is_success 为 False）的 item 列表。
    """
    if not items:
        return []

    remaining = list(items)
    permanent_failures: list[T] = []

    with tqdm(total=len(items), desc=desc, unit=unit) as pbar:
        while remaining:
            failed: list[T] = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_item = {executor.submit(fetch_fn, item): item for item in remaining}
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    result = future.result()
                    if should_retry(item, result):
                        failed.append(item)
                    else:
                        pbar.update(1)
                        if not is_success(item, result):
                            permanent_failures.append(item)
            remaining = failed
            if remaining:
                time.sleep(TUSHARE_RATE_LIMIT_RETRY_SLEEP_SEC)

    return permanent_failures


def retry_if_triplet_api_error(_item: object, result: object) -> bool:
    """(code, ok, n) 中 n == -1 表示接口异常，按限流重试。"""
    if not isinstance(result, tuple) or len(result) != 3:
        return False
    _code, ok, n = result
    return (not ok) and n == -1


def triplet_indicates_success(_item: object, result: object) -> bool:
    if not isinstance(result, tuple) or len(result) != 3:
        return False
    return bool(result[1])


def get_required_env(name: str) -> str:
    """获取必需的环境变量"""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"缺少环境变量 {name}，请参考 .env.example 配置")
    return value


def get_tushare_pro():
    """获取 Tushare pro_api 实例"""
    import tushare as ts

    token = get_required_env("TUSHARE_TOKEN")
    ts.set_token(token)
    return ts.pro_api(token)


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """保存 DataFrame 为 CSV 文件"""
    ensure_dir(path)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def file_exists_and_not_empty(path: Path) -> bool:
    """检查文件是否存在且非空"""
    return path.exists() and path.stat().st_size > 0
