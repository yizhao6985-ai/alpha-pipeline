from __future__ import annotations

from pathlib import Path

from .utils import ensure_directory, sanitize_for_filename


def _filename_part(value: str) -> str:
    return sanitize_for_filename(value).lower()


def _prefixed_ts_code_part(ts_code: str) -> str:
    normalized = _filename_part(ts_code)
    code, separator, market = normalized.partition("_")
    if separator and market:
        return f"{market}_{code}"
    return normalized


def _dated_base_dir(*, base_dir: Path, today_ymd: str) -> Path:
    return base_dir / today_ymd


def has_current_data(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def build_company_basic_info_path(*, base_dir: Path, today_ymd: str, exchange: str) -> Path:
    exchange_prefix_by_code = {
        "SSE": "sh",
        "SZSE": "sz",
    }
    exchange_prefix = exchange_prefix_by_code[exchange]
    path = (
        _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd)
        / "company"
        / "company_basic_info"
        / f"{exchange_prefix}_company_basic_info.csv"
    )
    ensure_directory(path.parent)
    return path


def build_stock_list_path(*, base_dir: Path, today_ymd: str, exchange: str) -> Path:
    exchange_prefix_by_code = {
        "SSE": "sh",
        "SZSE": "sz",
    }
    exchange_prefix = exchange_prefix_by_code[exchange]
    path = (
        _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd)
        / "stock"
        / "stock_list"
        / f"{exchange_prefix}_stock_list.csv"
    )
    ensure_directory(path.parent)
    return path


def build_stock_hsgt_list_path(
    *,
    base_dir: Path,
    today_ymd: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Path:
    parts = ["hsgt_stock_list"]
    if start_date or end_date:
        parts.append(f"{start_date or 'begin'}_{end_date or 'latest'}")
    path = (
        _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd)
        / "stock"
        / "hsgt_stock_list"
        / f"{'_'.join(parts)}.csv"
    )
    ensure_directory(path.parent)
    return path


def build_stock_st_list_path(*, base_dir: Path, today_ymd: str) -> Path:
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "stock" / "st_stock_list" / "st_stock_list.csv"
    ensure_directory(path.parent)
    return path


def build_quote_qfq_daily_path(
    *,
    base_dir: Path,
    today_ymd: str,
    ts_code: str,
    start_date: str,
    end_date: str,
) -> Path:
    parts = [_prefixed_ts_code_part(ts_code), "qfq_daily", f"{start_date}_{end_date}"]
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "quote" / "qfq_daily" / f"{'_'.join(parts)}.csv"
    ensure_directory(path.parent)
    return path


def build_quote_qfq_5min_path(
    *,
    base_dir: Path,
    today_ymd: str,
    ts_code: str,
    start_date: str,
    end_date: str,
) -> Path:
    parts = [_prefixed_ts_code_part(ts_code), "qfq_5min", f"{start_date}_{end_date}"]
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "quote" / "qfq_5min" / f"{'_'.join(parts)}.csv"
    ensure_directory(path.parent)
    return path


def build_quote_daily_basic_path(
    *,
    base_dir: Path,
    today_ymd: str,
    ts_code: str,
    start_date: str,
    end_date: str,
) -> Path:
    parts = [_prefixed_ts_code_part(ts_code), "daily_basic", f"{start_date}_{end_date}"]
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "quote" / "daily_basic" / f"{'_'.join(parts)}.csv"
    ensure_directory(path.parent)
    return path


def build_trade_calendar_path(
    *,
    base_dir: Path,
    today_ymd: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Path:
    parts = ["calendar"]
    if start_date or end_date:
        parts.append(f"{start_date or 'begin'}_{end_date or 'latest'}")
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "calendar" / "calendar" / f"{'_'.join(parts)}.csv"
    ensure_directory(path.parent)
    return path


def build_index_basic_source_dir(*, base_dir: Path, today_ymd: str, market: str) -> Path:
    market_prefix = sanitize_for_filename(market).lower()
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "index" / "index_basic" / market_prefix
    return ensure_directory(path)


def has_current_index_basic_data(*, base_dir: Path, today_ymd: str, market: str) -> bool:
    source_dir = build_index_basic_source_dir(base_dir=base_dir, today_ymd=today_ymd, market=market)
    if not source_dir.exists():
        return False
    return any(path.is_file() and path.stat().st_size > 0 for path in source_dir.rglob("*.csv"))


def build_index_basic_path(*, base_dir: Path, today_ymd: str, market: str, category: str) -> Path:
    market_prefix = sanitize_for_filename(market).lower()
    category_prefix = _filename_part(category)
    path = (
        _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd)
        / "index"
        / "index_basic"
        / market_prefix
        / category_prefix
        / f"{market_prefix}_{category_prefix}_index_basic.csv"
    )
    ensure_directory(path.parent)
    return path


def build_default_index_weight_paths(
    *,
    base_dir: Path,
    today_ymd: str,
    index_codes: tuple[str, ...],
    trade_date: str | None = None,
) -> list[Path]:
    return [
        build_index_weight_path(
            base_dir=base_dir,
            today_ymd=today_ymd,
            index_code=index_code,
            trade_date=trade_date,
        )
        for index_code in index_codes
    ]


def build_index_weight_path(
    *,
    base_dir: Path,
    today_ymd: str,
    index_code: str,
    trade_date: str | None = None,
) -> Path:
    parts = ["index_weight", _filename_part(index_code)]
    if trade_date:
        parts.append(trade_date)
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "index" / "index_weight" / f"{'_'.join(parts)}.csv"
    ensure_directory(path.parent)
    return path


def build_default_financial_statement_paths(
    *,
    base_dir: Path,
    today_ymd: str,
    ts_codes: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> list[Path]:
    paths: list[Path] = []
    for ts_code in ts_codes:
        paths.append(
            build_financial_statement_path(
                base_dir=base_dir,
                today_ymd=today_ymd,
                statement_type="balancesheet",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        )
        paths.append(
            build_financial_statement_path(
                base_dir=base_dir,
                today_ymd=today_ymd,
                statement_type="income",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        )
        paths.append(
            build_financial_statement_path(
                base_dir=base_dir,
                today_ymd=today_ymd,
                statement_type="cashflow",
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )
        )
    return paths


def build_financial_statement_path(
    *,
    base_dir: Path,
    today_ymd: str,
    statement_type: str,
    ts_code: str,
    ann_date: str | None = None,
    f_ann_date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    period: str | None = None,
    report_type: str | None = None,
    comp_type: str | None = None,
    is_calc: int | None = None,
) -> Path:
    parts = [_prefixed_ts_code_part(ts_code), statement_type.lower()]
    if period:
        parts.append(period)
    elif start_date or end_date:
        parts.append(f"{start_date or 'begin'}_{end_date or 'latest'}")
    if ann_date:
        parts.append(f"ann_{ann_date}")
    if f_ann_date:
        parts.append(f"fann_{f_ann_date}")
    if report_type:
        parts.append(f"report_{report_type}")
    if comp_type:
        parts.append(f"comp_{comp_type}")
    if is_calc is not None:
        parts.append(f"calc_{is_calc}")
    path = _dated_base_dir(base_dir=base_dir, today_ymd=today_ymd) / "company" / "financial" / statement_type / f"{'_'.join(parts)}.csv"
    ensure_directory(path.parent)
    return path
