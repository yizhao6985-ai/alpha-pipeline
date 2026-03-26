#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_qlib_bin(bin_path: Path) -> tuple[int, list[float]]:
    raw = bin_path.read_bytes()
    if len(raw) < 4:
        raise ValueError(f"文件过小，无法读取头部 int32: {bin_path}")
    if (len(raw) - 4) % 4 != 0:
        raise ValueError(f"文件长度异常，特征区不是 float32 对齐: {bin_path}")

    start_index = struct.unpack("<i", raw[:4])[0]
    values = [value[0] for value in struct.iter_unpack("<f", raw[4:])]
    return start_index, values


def read_calendar(calendar_path: Path) -> list[str]:
    if not calendar_path.exists():
        raise FileNotFoundError(f"找不到交易日历文件: {calendar_path}")
    lines = calendar_path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将 Qlib .bin 特征文件还原为带日期的 CSV")
    parser.add_argument("bin_path", type=Path, help="Qlib 特征 .bin 文件路径")
    parser.add_argument("calendar_path", type=Path, help="Qlib 交易日历路径，例如 calendars/day.txt")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help='输出 CSV 路径，默认保存到 "qlib_data/<bin文件名>.csv"',
    )
    parser.add_argument(
        "--column",
        type=str,
        default=None,
        help="值列名，默认使用 .bin 文件名（不含后缀）",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    bin_path: Path = args.bin_path
    output_csv = args.output_csv or (ROOT / "qlib_data" / f"{bin_path.stem}.csv")
    value_col = args.column or bin_path.stem

    start_index, values = read_qlib_bin(bin_path)
    calendar = read_calendar(args.calendar_path)

    if start_index < 0:
        raise ValueError(f"start_index 不能为负数: {start_index}")
    if start_index >= len(calendar):
        raise ValueError(
            f"start_index={start_index} 超出 calendar 范围（长度={len(calendar)}），无法映射日期"
        )

    end_exclusive = start_index + len(values)
    if end_exclusive > len(calendar):
        valid_len = len(calendar) - start_index
        print(
            f"警告: 值数量({len(values)})超出 calendar 可映射范围，仅保留前 {valid_len} 条以导出"
        )
        values = values[:valid_len]

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        writer.writerow(["trade_date", value_col])
        for offset, value in enumerate(values):
            trade_date = calendar[start_index + offset]
            writer.writerow([trade_date, value])

    print(f"已导出: {output_csv}")
    print(f"记录数: {len(values)}")


if __name__ == "__main__":
    main()
