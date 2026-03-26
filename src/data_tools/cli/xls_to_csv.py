from __future__ import annotations

import argparse
from pathlib import Path

from data_tools.converters.xls_to_csv import convert_xls_to_csv


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

