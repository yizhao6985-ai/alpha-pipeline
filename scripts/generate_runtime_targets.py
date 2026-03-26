#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_fetch.runtime import build_runtime_targets_payload, write_runtime_targets
from data_fetch.utils import normalize_codes, normalize_strings


def _split_values(values: list[str]) -> list[str]:
    normalized_values: list[str] = []
    for raw_value in values:
        for item in raw_value.split(","):
            normalized = item.strip()
            if normalized and normalized not in normalized_values:
                normalized_values.append(normalized)
    return normalized_values


def build_targets(args: argparse.Namespace) -> dict[str, list[str]]:
    # TODO: 在这里补充你的运行时目标生成逻辑。
    # 当前先支持通过命令行手动传入，便于验证 runtime 机制。
    return build_runtime_targets_payload(
        ts_codes=normalize_codes(_split_values(args.ts_codes)),
        index_codes=normalize_codes(_split_values(args.index_codes)),
        index_basic_markets=normalize_codes(_split_values(args.index_basic_markets)),
        stock_index_basic_categories=normalize_strings(_split_values(args.stock_index_basic_categories)),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成 runtime/targets.json")
    parser.add_argument(
        "--ts-code",
        dest="ts_codes",
        action="append",
        default=[],
        help="公司 ts_code，可重复传入，也支持逗号分隔",
    )
    parser.add_argument(
        "--index-code",
        dest="index_codes",
        action="append",
        default=[],
        help="指数 index_code，可重复传入，也支持逗号分隔",
    )
    parser.add_argument(
        "--index-basic-market",
        dest="index_basic_markets",
        action="append",
        default=[],
        help="指数基础信息来源 market，可重复传入，也支持逗号分隔",
    )
    parser.add_argument(
        "--stock-index-basic-category",
        dest="stock_index_basic_categories",
        action="append",
        default=[],
        help="股票类指数基础信息类别，可重复传入，也支持逗号分隔",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = build_targets(args)
    output_path = write_runtime_targets(
        ts_codes=payload["ts_codes"],
        index_codes=payload["index_codes"],
        index_basic_markets=payload["index_basic_markets"],
        stock_index_basic_categories=payload["stock_index_basic_categories"],
        project_root=ROOT,
    )
    print(f"已生成 runtime targets 文件: {output_path}")
    print(f"- ts_codes: {len(payload['ts_codes'])}")
    print(f"- index_codes: {len(payload['index_codes'])}")
    print(f"- index_basic_markets: {len(payload['index_basic_markets'])}")
    print(f"- stock_index_basic_categories: {len(payload['stock_index_basic_categories'])}")


if __name__ == "__main__":
    main()
