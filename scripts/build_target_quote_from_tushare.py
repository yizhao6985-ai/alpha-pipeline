from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


OUTPUT_COLUMNS = [
    "date",
    "symbol",
    "adjclose",
    "amount",
    "change",
    "close",
    "factor",
    "high",
    "low",
    "open",
    "volume",
    "vwap",
]

DECIMAL_MAX_PLACES: dict[str, int] = {
    "adjclose": 2,
    "amount": 3,
    "change": 9,
    "close": 7,
    "factor": 8,
    "high": 7,
    "low": 7,
    "open": 7,
    "volume": 2,
    "vwap": 7,
}


def to_symbol(ts_code: str) -> str:
    code, market = ts_code.split(".")
    return f"{market}{code}"


def format_date(yyyymmdd: str) -> str:
    raw = yyyymmdd.strip()
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def as_float(row: dict[str, str], key: str) -> float:
    value = row.get(key, "").strip()
    if not value:
        raise ValueError(f"字段为空: {key}")
    return float(value)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"CSV 头部为空: {path}")
        return [{(k or "").strip(): (v or "").strip() for k, v in row.items()} for row in reader]


def load_adj_factor_map(adj_path: Path) -> dict[str, float]:
    rows = read_csv_rows(adj_path)
    mapping: dict[str, float] = {}
    for row in rows:
        trade_date = row.get("trade_date", "")
        factor = row.get("adj_factor", "")
        if trade_date and factor:
            mapping[trade_date] = float(factor)
    return mapping


def load_factor_by_date(factor_file: Path) -> dict[str, float]:
    rows = read_csv_rows(factor_file)
    result: dict[str, float] = {}
    for row in rows:
        date = row.get("date", "")
        factor = row.get("factor", "")
        if date and factor:
            result[date] = float(factor)
    if not result:
        raise ValueError(f"factor 文件为空或缺少 date/factor: {factor_file}")
    return result


def transform_rows(
    *,
    qfq_rows: list[dict[str, str]],
    adj_map: dict[str, float] | None,
    factor_mode: str,
    factor_value: float | None,
    factor_by_date: dict[str, float] | None,
    vwap_multiplier: float,
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    required_fields = {"ts_code", "trade_date", "open", "high", "low", "close", "pre_close", "change", "vol", "amount"}
    if not qfq_rows:
        return []
    missing = required_fields - set(qfq_rows[0].keys())
    if missing:
        raise ValueError(f"qfq 文件缺少字段: {sorted(missing)}")

    rows = sorted(qfq_rows, key=lambda r: r["trade_date"])
    prepared: list[dict[str, Any]] = []
    for row in rows:
        date = format_date(row["trade_date"])
        if start_date and date < start_date:
            continue
        if end_date and date > end_date:
            continue

        adj_factor_raw = row.get("adj_factor", "")
        if adj_factor_raw:
            adj_factor = float(adj_factor_raw)
        elif adj_map is not None and row["trade_date"] in adj_map:
            adj_factor = adj_map[row["trade_date"]]
        else:
            raise ValueError(f"缺少 adj_factor: trade_date={row['trade_date']}")

        close = as_float(row, "close")
        prepared.append(
            {
                "date": date,
                "symbol": to_symbol(row["ts_code"]),
                "open_raw": as_float(row, "open"),
                "high_raw": as_float(row, "high"),
                "low_raw": as_float(row, "low"),
                "close_raw": close,
                "pre_close_raw": as_float(row, "pre_close"),
                "change_raw": as_float(row, "change"),
                "volume_raw": as_float(row, "vol"),
                "amount_raw": as_float(row, "amount"),
                "adjclose": close * adj_factor,
            }
        )

    if not prepared:
        return []

    first_adjclose = prepared[0]["adjclose"]
    if first_adjclose == 0:
        raise ValueError("首日 adjclose 为 0，无法计算 factor")

    output: list[dict[str, Any]] = []
    for row in prepared:
        if factor_mode == "first-adjclose":
            factor = 1.0 / first_adjclose
        elif factor_mode == "constant":
            if factor_value is None:
                raise ValueError("factor-mode=constant 时必须传 --factor-value")
            factor = factor_value
        elif factor_mode == "from-file":
            if factor_by_date is None:
                raise ValueError("factor-mode=from-file 时必须传 --factor-file")
            if row["date"] not in factor_by_date:
                raise ValueError(f"factor 文件缺少日期: {row['date']}")
            factor = factor_by_date[row["date"]]
        else:
            raise ValueError(f"不支持的 factor 模式: {factor_mode}")

        if factor == 0:
            raise ValueError(f"factor 为 0: {row['date']}")

        volume = row["volume_raw"] / factor
        close = row["close_raw"] * factor
        output.append(
            {
                "date": row["date"],
                "symbol": row["symbol"],
                "adjclose": row["adjclose"],
                "amount": row["amount_raw"],
                "change": row["change_raw"] / row["pre_close_raw"],
                "close": close,
                "factor": factor,
                "high": row["high_raw"] * factor,
                "low": row["low_raw"] * factor,
                "open": row["open_raw"] * factor,
                "volume": volume,
                "vwap": (row["amount_raw"] / volume) * vwap_multiplier,
            }
        )
    return output


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    def fmt(value: Any, key: str) -> Any:
        if key in {"date", "symbol"}:
            return value
        max_places = DECIMAL_MAX_PLACES.get(key)
        if max_places is None:
            return value
        num = float(value)
        text = f"{num:.{max_places}f}".rstrip("0").rstrip(".")
        # 避免出现 "-0"
        return "0" if text in {"-0", "-0.0", ""} else text

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: fmt(row[key], key) for key in OUTPUT_COLUMNS})


def run_single(
    *,
    qfq_path: Path,
    adj_path: Path | None,
    output_path: Path,
    factor_mode: str,
    factor_value: float | None,
    factor_file: Path | None,
    vwap_multiplier: float,
    start_date: str | None,
    end_date: str | None,
) -> int:
    qfq_rows = read_csv_rows(qfq_path)
    adj_map = load_adj_factor_map(adj_path) if adj_path is not None else None
    factor_by_date = load_factor_by_date(factor_file) if factor_file is not None else None
    output_rows = transform_rows(
        qfq_rows=qfq_rows,
        adj_map=adj_map,
        factor_mode=factor_mode,
        factor_value=factor_value,
        factor_by_date=factor_by_date,
        vwap_multiplier=vwap_multiplier,
        start_date=start_date,
        end_date=end_date,
    )
    if not output_rows:
        raise ValueError(f"筛选后无数据: {qfq_path}")
    write_rows(output_path, output_rows)
    print(f"已生成: {output_path} ({len(output_rows)} 条)")
    return len(output_rows)


def infer_adj_path(adj_dir: Path, qfq_file_name: str) -> Path:
    return adj_dir / qfq_file_name.replace("_qfq_daily_", "_adj_factor_")


def infer_output_name_from_qfq_file(qfq_file_name: str) -> str:
    # e.g. sh_600006_qfq_daily_20180101_20260326.csv -> SH600006.csv
    stem = qfq_file_name.replace(".csv", "")
    parts = stem.split("_")
    if len(parts) < 2:
        raise ValueError(f"无法从文件名解析股票代码: {qfq_file_name}")
    market, code = parts[0].upper(), parts[1]
    if market not in {"SH", "SZ", "BJ"}:
        raise ValueError(f"不支持的市场前缀: {qfq_file_name}")
    if not code.isdigit():
        raise ValueError(f"不支持的股票代码部分: {qfq_file_name}")
    return f"{market}{code}.csv"


def infer_date_from_qfq_dir(qfq_dir: Path) -> str:
    # expected: data/<YYYYMMDD>/quote/qfq_daily
    parts = qfq_dir.parts
    for idx, value in enumerate(parts):
        if value == "data" and idx + 1 < len(parts):
            date_part = parts[idx + 1]
            if len(date_part) == 8 and date_part.isdigit():
                return date_part
    raise ValueError(f"无法从 qfq 目录推断日期，请显式传 --output-dir: {qfq_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="从 Tushare qfq_daily/adj_factor 生成目标格式行情（支持批量）")
    parser.add_argument("--qfq", type=Path, default=None, help="单文件模式：qfq_daily CSV 路径")
    parser.add_argument("--adj", type=Path, default=None, help="单文件模式：adj_factor CSV 路径（可选）")
    parser.add_argument("--output", type=Path, default=None, help="单文件模式：输出 CSV 路径")
    parser.add_argument("--qfq-dir", type=Path, default=None, help="批量模式：qfq_daily 目录路径")
    parser.add_argument("--adj-dir", type=Path, default=None, help="批量模式：adj_factor 目录路径（可选）")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="批量模式：输出目录路径，默认自动推断为 qlib_data/<日期>/feature",
    )
    parser.add_argument(
        "--factor-mode",
        choices=("first-adjclose", "constant", "from-file"),
        default="first-adjclose",
        help="因子生成方式：首日归一化/固定值/按日期文件",
    )
    parser.add_argument("--factor-value", type=float, default=None, help="固定因子值（factor-mode=constant 时必填）")
    parser.add_argument(
        "--factor-file",
        type=Path,
        default=None,
        help="按日期因子文件，需包含 date,factor 两列（factor-mode=from-file 时必填）",
    )
    parser.add_argument("--vwap-multiplier", type=float, default=10.0, help="vwap 乘数，默认 10")
    parser.add_argument("--start-date", type=str, default=None, help="起始日期（YYYY-MM-DD）")
    parser.add_argument("--end-date", type=str, default=None, help="结束日期（YYYY-MM-DD）")
    args = parser.parse_args()
    single_mode = args.qfq is not None or args.output is not None
    batch_mode = args.qfq_dir is not None or args.output_dir is not None
    if single_mode and batch_mode:
        raise ValueError("请二选一：单文件模式(--qfq/--output) 或 批量模式(--qfq-dir/--output-dir)")
    if not single_mode and not batch_mode:
        raise ValueError("必须选择一种模式：单文件模式或批量模式")

    if single_mode:
        if args.qfq is None or args.output is None:
            raise ValueError("单文件模式必须同时提供 --qfq 和 --output")
        run_single(
            qfq_path=args.qfq,
            adj_path=args.adj,
            output_path=args.output,
            factor_mode=args.factor_mode,
            factor_value=args.factor_value,
            factor_file=args.factor_file,
            vwap_multiplier=args.vwap_multiplier,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        return

    if args.qfq_dir is None:
        raise ValueError("批量模式必须提供 --qfq-dir")
    if args.output_dir is None:
        date_part = infer_date_from_qfq_dir(args.qfq_dir)
        args.output_dir = Path("qlib_data") / date_part / "feature"
    qfq_files = sorted(args.qfq_dir.glob("*.csv"))
    if not qfq_files:
        raise ValueError(f"qfq 目录下没有 CSV 文件: {args.qfq_dir}")

    success = 0
    failed = 0
    for qfq_path in qfq_files:
        output_name = infer_output_name_from_qfq_file(qfq_path.name)
        output_path = args.output_dir / output_name
        adj_path = None
        if args.adj_dir is not None:
            candidate = infer_adj_path(args.adj_dir, qfq_path.name)
            if candidate.exists():
                adj_path = candidate
        try:
            run_single(
                qfq_path=qfq_path,
                adj_path=adj_path,
                output_path=output_path,
                factor_mode=args.factor_mode,
                factor_value=args.factor_value,
                factor_file=args.factor_file,
                vwap_multiplier=args.vwap_multiplier,
                start_date=args.start_date,
                end_date=args.end_date,
            )
            success += 1
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"生成失败: {qfq_path} -> {output_path}\n  原因: {exc!r}")
    print(f"批量完成：成功 {success}，失败 {failed}")


if __name__ == "__main__":
    main()
