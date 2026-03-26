from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import shutil


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_for_filename(value: str) -> str:
    return value.replace(".", "_").replace("/", "_")


def normalize_codes(values: Iterable[str]) -> tuple[str, ...]:
    normalized_values = []
    for item in values:
        normalized = item.strip().upper()
        if normalized and normalized not in normalized_values:
            normalized_values.append(normalized)
    return tuple(normalized_values)


def normalize_strings(values: Iterable[str]) -> tuple[str, ...]:
    normalized_values = []
    for item in values:
        normalized = item.strip()
        if normalized and normalized not in normalized_values:
            normalized_values.append(normalized)
    return tuple(normalized_values)


def reset_today_output_dir(
    *,
    output_dir: Path,
    today_ymd: str,
    has_index_weights: bool,
    has_ts_codes: bool,
    skip_financial: bool,
    skip_qfq_daily: bool,
    skip_qfq_5min: bool,
    skip_daily_basic: bool,
    skip_adj_factor: bool,
) -> None:
    today_dir = output_dir / today_ymd
    targets: list[Path] = [
        today_dir / "index" / "index_basic",
        today_dir / "stock" / "hsgt_stock_list",
        today_dir / "stock" / "stock_list",
        today_dir / "stock" / "st_stock_list",
        today_dir / "company" / "company_basic_info",
        today_dir / "calendar" / "calendar",
    ]
    if has_index_weights:
        targets.append(today_dir / "index" / "index_weight")
    if has_ts_codes:
        if not skip_qfq_daily:
            targets.append(today_dir / "stock" / "qfq_daily")
            targets.append(today_dir / "quote" / "qfq_daily")
        if not skip_qfq_5min:
            targets.append(today_dir / "stock" / "qfq_5min")
            targets.append(today_dir / "quote" / "qfq_5min")
        if not skip_daily_basic:
            targets.append(today_dir / "stock" / "daily_basic")
            targets.append(today_dir / "quote" / "daily_basic")
        if not skip_adj_factor:
            targets.append(today_dir / "stock" / "adj_factor")
            targets.append(today_dir / "quote" / "adj_factor")
        if not skip_financial:
            targets.append(today_dir / "company" / "financial")

    for target in targets:
        if target.exists():
            shutil.rmtree(target)
            print(f"已删除将重新获取的数据目录: {target}")
