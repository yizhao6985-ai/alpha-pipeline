#!/usr/bin/env python3
"""
XLS 转 CSV 工具

用法:
    python scripts/xls_to_csv.py data/download/file.xls
    python scripts/xls_to_csv.py data/download/file.xls --sheet-name "Sheet1"
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def open_workbook(xls_path: Path):
    try:
        import xlrd  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("未安装 xlrd，无法读取 .xls。请先执行: pip install xlrd") from exc
    return xlrd.open_workbook(str(xls_path))


def cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def convert_xls_to_csv(
    *,
    xls_path: Path,
    output_csv: Path | None = None,
    sheet_name: str | None = None,
    sheet_index: int = 0,
) -> tuple[Path, str, int]:
    if not xls_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {xls_path}")

    out_csv = output_csv or xls_path.with_suffix(".csv")
    workbook = open_workbook(xls_path)
    sheet = workbook.sheet_by_name(sheet_name) if sheet_name else workbook.sheet_by_index(sheet_index)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        for row_idx in range(sheet.nrows):
            row_values = [cell_to_text(cell) for cell in sheet.row_values(row_idx)]
            writer.writerow(row_values)

    return out_csv, sheet.name, sheet.nrows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将 .xls 文件转换为 .csv")
    parser.add_argument("xls_path", type=Path, help="输入 .xls 文件路径")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="输出 csv 路径，默认与 xls 同目录同名",
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        default=None,
        help="指定工作表名称，默认使用第一个工作表",
    )
    parser.add_argument(
        "--sheet-index",
        type=int,
        default=0,
        help="指定工作表索引（从0开始），当未传 --sheet-name 时生效",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    out_csv, used_sheet_name, row_count = convert_xls_to_csv(
        xls_path=args.xls_path,
        output_csv=args.output_csv,
        sheet_name=args.sheet_name,
        sheet_index=args.sheet_index,
    )
    print(f"已转换: {args.xls_path}")
    print(f"输出文件: {out_csv}")
    print(f"sheet: {used_sheet_name}")
    print(f"行数: {row_count}")


if __name__ == "__main__":
    main()
