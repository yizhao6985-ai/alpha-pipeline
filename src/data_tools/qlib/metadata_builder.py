from __future__ import annotations

from pathlib import Path

from data_tools.io.csv_reader import find_single_file, read_csv_rows

DEFAULT_END_DATE = "20991231"
CSI1000_INDEX_CODE = "000852.SH"


def format_date_yyyy_mm_dd(date_str: str) -> str:
    raw = date_str.strip()
    if len(raw) == 8 and raw.isdigit():
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    return raw


def to_qlib_symbol(ts_code: str) -> str:
    code, _, market = ts_code.strip().upper().partition(".")
    if not code or not market:
        raise ValueError(f"非法 ts_code: {ts_code}")
    return f"{market}{code}"


def load_trade_days(date_dir: Path) -> list[str]:
    calendar_dir = date_dir / "calendar" / "calendar"
    calendar_files = sorted(calendar_dir.rglob("calendar*.csv")) if calendar_dir.exists() else []
    if calendar_files:
        rows = read_csv_rows(calendar_files[0])
        if not rows:
            raise ValueError(f"交易日历为空: {calendar_files[0]}")

        open_days = [
            row.get("cal_date", "")
            for row in rows
            if row.get("is_open", "") == "1" and row.get("cal_date", "")
        ]
        if open_days:
            return sorted(set(open_days))

    quote_dir = date_dir / "quote" / "qfq_daily"
    quote_files = sorted(quote_dir.rglob("*.csv")) if quote_dir.exists() else []
    if not quote_files:
        raise FileNotFoundError(
            f"既未找到交易日历，也未找到可推导日期的 qfq_daily 文件: {calendar_dir} / {quote_dir}"
        )
    rows = read_csv_rows(quote_files[0])
    trade_days = sorted({row.get("trade_date", "") for row in rows if row.get("trade_date", "")})
    if not trade_days:
        raise ValueError(f"无法从 qfq_daily 推导交易日: {quote_files[0]}")
    return trade_days


def write_days(qlib_date_dir: Path, trade_days: list[str]) -> tuple[Path, Path]:
    calendars_dir = qlib_date_dir / "calendars"
    calendars_dir.mkdir(parents=True, exist_ok=True)

    day_path = calendars_dir / "day.txt"
    day_future_path = calendars_dir / "day_future.txt"
    formatted_days = [format_date_yyyy_mm_dd(day) for day in trade_days]
    content = "\n".join(formatted_days) + "\n"
    day_path.write_text(content, encoding="utf-8")
    day_future_path.write_text(content, encoding="utf-8")
    return day_path, day_future_path


def load_all_instruments(date_dir: Path) -> dict[str, tuple[str, str, str]]:
    stock_list_dir = date_dir / "stock" / "stock_list"
    sh_path = stock_list_dir / "sh_stock_list.csv"
    sz_path = stock_list_dir / "sz_stock_list.csv"
    if not sh_path.exists() or not sz_path.exists():
        raise FileNotFoundError(f"未找到 A 股列表文件: {sh_path} 或 {sz_path}")

    instruments: dict[str, tuple[str, str, str]] = {}
    for csv_path in (sh_path, sz_path):
        for row in read_csv_rows(csv_path):
            ts_code = row.get("ts_code", "").upper()
            if not ts_code:
                continue
            qlib_symbol = to_qlib_symbol(ts_code)
            start_date = row.get("list_date", "") or "19000101"
            end_date = row.get("delist_date", "") or DEFAULT_END_DATE
            instruments[ts_code] = (qlib_symbol, start_date, end_date)
    if not instruments:
        raise ValueError("未从 stock_list 中解析出任何股票")
    return instruments


def write_instruments(path: Path, rows: list[tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{symbol}\t{format_date_yyyy_mm_dd(start)}\t{format_date_yyyy_mm_dd(end)}"
        for symbol, start, end in rows
    ]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def load_csi1000_members(date_dir: Path) -> list[str]:
    weight_dir = date_dir / "index" / "index_weight"
    preferred = weight_dir / f"index_weight_{CSI1000_INDEX_CODE}.csv"
    if preferred.exists():
        weight_path = preferred
    else:
        weight_path = find_single_file(
            weight_dir,
            "index_weight_000852*.csv",
            "中证1000成分权重 CSV（000852.SH）",
        )

    members: set[str] = set()
    for row in read_csv_rows(weight_path):
        con_code = row.get("con_code", "").upper()
        if con_code:
            members.add(con_code)
    if not members:
        raise ValueError(f"中证1000权重文件无 con_code 数据: {weight_path}")
    return sorted(members)


def generate_qlib_metadata(*, date: str, data_root: Path, output_root: Path) -> None:
    date_dir = data_root / date
    if not date_dir.exists():
        raise FileNotFoundError(f"日期目录不存在: {date_dir}")
    qlib_date_dir = output_root / date

    trade_days = load_trade_days(date_dir)
    day_path, day_future_path = write_days(qlib_date_dir, trade_days)

    all_instruments = load_all_instruments(date_dir)
    all_rows = sorted(all_instruments.values(), key=lambda item: item[0])
    all_txt_path = qlib_date_dir / "instruments" / "all.txt"
    write_instruments(all_txt_path, all_rows)

    csi1000_codes = load_csi1000_members(date_dir)
    csi1000_rows = [all_instruments[ts_code] for ts_code in csi1000_codes if ts_code in all_instruments]
    csi1000_rows.sort(key=lambda item: item[0])
    csi1000_txt_path = qlib_date_dir / "instruments" / "csi1000.txt"
    write_instruments(csi1000_txt_path, csi1000_rows)

    print(f"已生成: {day_path}")
    print(f"已生成: {day_future_path}")
    print(f"已生成: {all_txt_path} ({len(all_rows)} 条)")
    print(f"已生成: {csi1000_txt_path} ({len(csi1000_rows)} 条)")
    missing_count = len(csi1000_codes) - len(csi1000_rows)
    if missing_count > 0:
        print(f"提示: CSI1000 有 {missing_count} 个成分股不在当日 A 股列表中，已自动跳过")

