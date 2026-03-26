#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path


def read_qlib_bin(bin_path: Path) -> tuple[int, list[float]]:
    raw = bin_path.read_bytes()
    if len(raw) < 4:
        raise ValueError(f"文件过小，无法读取头部 int32: {bin_path}")
    if (len(raw) - 4) % 4 != 0:
        raise ValueError(f"文件长度异常，特征区不是 float32 对齐: {bin_path}")

    start_index = struct.unpack("<i", raw[:4])[0]
    value_count = (len(raw) - 4) // 4
    values = [value[0] for value in struct.iter_unpack("<f", raw[4 : 4 + value_count * 4])]
    return start_index, values


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="读取 Qlib .bin 文件并打印摘要")
    parser.add_argument("bin_path", type=Path, help="Qlib 特征 .bin 文件路径")
    parser.add_argument(
        "--preview",
        type=int,
        default=10,
        help="预览前 N 个值，默认 10",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    start_index, values = read_qlib_bin(args.bin_path)

    total_count = len(values)
    nan_count = sum(1 for value in values if math.isnan(value))
    finite_values = [value for value in values if math.isfinite(value)]

    print(f"文件: {args.bin_path}")
    print(f"start_index: {start_index}")
    print(f"value_count: {total_count}")
    print(f"nan_count: {nan_count}")
    if finite_values:
        print(f"min: {min(finite_values)}")
        print(f"max: {max(finite_values)}")
    else:
        print("min/max: 无有限值")

    preview_size = max(0, args.preview)
    if preview_size > 0:
        print(f"preview({preview_size}): {values[:preview_size]}")


if __name__ == "__main__":
    main()
