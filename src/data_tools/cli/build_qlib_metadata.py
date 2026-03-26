from __future__ import annotations

import argparse
from pathlib import Path

from data_tools.qlib.metadata_builder import generate_qlib_metadata


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="按日期从 data 生成 Qlib 的 calendars/instruments 文件")
    parser.add_argument("date", type=str, help="目标日期目录，例如 20260324")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=root / "data",
        help='原始数据根目录，默认 "data"',
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=root / "qlib_data",
        help='Qlib 输出根目录，默认 "qlib_data"',
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    generate_qlib_metadata(date=args.date, data_root=args.data_root, output_root=args.output_root)

