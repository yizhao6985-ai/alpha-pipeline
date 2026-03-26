from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .utils import normalize_codes, normalize_strings

DEFAULT_TS_CODES = ("600000.SH", "000001.SZ")
DEFAULT_INDEX_CODES = ("399300.SZ", "000001.SH")
DEFAULT_TARGET_CODES_FILENAME = "targets.json"
DEFAULT_INDEX_BASIC_MARKETS = ("CSI", "SSE", "SZSE")
DEFAULT_STOCK_INDEX_BASIC_CATEGORIES = (
    "主题指数",
    "规模指数",
    "策略指数",
    "风格指数",
    "综合指数",
    "行业指数",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def ensure_runtime_dir(project_root: str | Path = PROJECT_ROOT) -> Path:
    root = Path(project_root)
    runtime_dir = root / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def get_default_targets_file(project_root: str | Path = PROJECT_ROOT) -> Path:
    return ensure_runtime_dir(project_root) / DEFAULT_TARGET_CODES_FILENAME


def build_runtime_targets_payload(
    *,
    ts_codes: Iterable[str] = (),
    index_codes: Iterable[str] = (),
    index_basic_markets: Iterable[str] = DEFAULT_INDEX_BASIC_MARKETS,
    stock_index_basic_categories: Iterable[str] = DEFAULT_STOCK_INDEX_BASIC_CATEGORIES,
) -> dict[str, list[str]]:
    resolved_markets = index_basic_markets or DEFAULT_INDEX_BASIC_MARKETS
    resolved_categories = stock_index_basic_categories or DEFAULT_STOCK_INDEX_BASIC_CATEGORIES
    return {
        "ts_codes": list(normalize_codes(ts_codes)),
        "index_codes": list(normalize_codes(index_codes)),
        "index_basic_markets": list(normalize_codes(resolved_markets)),
        "stock_index_basic_categories": list(normalize_strings(resolved_categories)),
    }


def write_runtime_targets(
    *,
    ts_codes: Iterable[str] = (),
    index_codes: Iterable[str] = (),
    index_basic_markets: Iterable[str] = DEFAULT_INDEX_BASIC_MARKETS,
    stock_index_basic_categories: Iterable[str] = DEFAULT_STOCK_INDEX_BASIC_CATEGORIES,
    project_root: str | Path = PROJECT_ROOT,
) -> Path:
    targets_file = get_default_targets_file(project_root)
    payload = build_runtime_targets_payload(
        ts_codes=ts_codes,
        index_codes=index_codes,
        index_basic_markets=index_basic_markets,
        stock_index_basic_categories=stock_index_basic_categories,
    )
    targets_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return targets_file


def _load_runtime_targets(targets_file: Path) -> dict[str, object] | None:
    if not targets_file.exists():
        return None

    try:
        payload = json.loads(targets_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"runtime targets 文件不是合法 JSON: {targets_file}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"runtime targets 文件内容必须是 JSON 对象: {targets_file}")

    return payload


def _get_runtime_code_values(targets_file: Path, key: str) -> tuple[str, ...] | None:
    payload = _load_runtime_targets(targets_file)
    if payload is None or key not in payload:
        return None

    value = payload[key]
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"runtime targets 字段 {key} 必须是字符串数组: {targets_file}")

    return normalize_codes(value)


def _get_runtime_string_values(targets_file: Path, key: str) -> tuple[str, ...] | None:
    payload = _load_runtime_targets(targets_file)
    if payload is None or key not in payload:
        return None

    value = payload[key]
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"runtime targets 字段 {key} 必须是字符串数组: {targets_file}")

    return normalize_strings(value)


def get_default_ts_codes(project_root: str | Path = PROJECT_ROOT) -> tuple[str, ...]:
    runtime_values = _get_runtime_code_values(get_default_targets_file(project_root), "ts_codes")
    if runtime_values is not None:
        return runtime_values
    return DEFAULT_TS_CODES


def get_runtime_ts_codes(project_root: str | Path = PROJECT_ROOT) -> tuple[str, ...]:
    runtime_values = _get_runtime_code_values(get_default_targets_file(project_root), "ts_codes")
    if runtime_values is not None:
        return runtime_values
    return ()


def get_default_index_codes(project_root: str | Path = PROJECT_ROOT) -> tuple[str, ...]:
    runtime_values = _get_runtime_code_values(get_default_targets_file(project_root), "index_codes")
    if runtime_values is not None:
        return runtime_values
    return DEFAULT_INDEX_CODES


def get_default_index_basic_markets(project_root: str | Path = PROJECT_ROOT) -> tuple[str, ...]:
    runtime_values = _get_runtime_code_values(get_default_targets_file(project_root), "index_basic_markets")
    if runtime_values is not None:
        return runtime_values
    return DEFAULT_INDEX_BASIC_MARKETS


def get_default_stock_index_basic_categories(project_root: str | Path = PROJECT_ROOT) -> tuple[str, ...]:
    runtime_values = _get_runtime_string_values(
        get_default_targets_file(project_root),
        "stock_index_basic_categories",
    )
    if runtime_values is not None:
        return runtime_values
    return DEFAULT_STOCK_INDEX_BASIC_CATEGORIES
