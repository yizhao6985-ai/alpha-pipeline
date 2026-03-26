from __future__ import annotations

import shutil
from pathlib import Path

from ..config import get_default_fetch_end_date, get_default_fetch_start_date
from ..runtime import get_default_index_basic_markets, get_default_index_codes, get_runtime_ts_codes


def resolve_runtime_defaults() -> tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    today_ymd = get_default_fetch_end_date()
    default_start_date = get_default_fetch_start_date()
    default_index_codes = get_default_index_codes()
    index_basic_markets = get_default_index_basic_markets()
    default_ts_codes = get_runtime_ts_codes()
    return (
        today_ymd,
        default_start_date,
        default_index_codes,
        index_basic_markets,
        default_ts_codes,
    )


def reset_today_output_dir(*, output_dir: Path, today_ymd: str) -> None:
    today_dir = output_dir / today_ymd
    if today_dir.exists():
        shutil.rmtree(today_dir)
        print(f"已删除当日目录，准备重新下载: {today_dir}")
