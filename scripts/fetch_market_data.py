#!/usr/bin/env python3
"""
数据获取脚本：从 Tushare 获取市场数据并保存为 CSV

用法:
    python scripts/fetch_market_data.py
    python scripts/fetch_market_data.py --ts-codes 600000.SH,000001.SZ
    python scripts/fetch_market_data.py --skip-financial --skip-qfq-daily
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 添加 scripts 目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fetchers import (
    fetch_stock_list,
    get_all_stock_codes,
    fetch_stock_hsgt,
    fetch_stock_st,
    fetch_company_basic_info,
    fetch_financial_statements,
    fetch_index_basic,
    fetch_index_weight,
    fetch_trade_calendar,
    fetch_qfq_daily,
    fetch_daily_basic,
    fetch_adj_factor,
    get_tushare_pro,
)

# 常量
DEFAULT_FETCH_START_DATE = "20180101"
DEFAULT_INDEX_CODES = ["399300.SZ", "000001.SH"]


def get_default_fetch_end_date() -> str:
    return datetime.today().strftime("%Y%m%d")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="数据获取: 获取并分类保存市场数据")
    parser.add_argument("--output-dir", type=str, default="data", help='输出根目录，默认 "data"')
    parser.add_argument("--start-date", type=str, default=DEFAULT_FETCH_START_DATE, help=f"开始日期，默认 {DEFAULT_FETCH_START_DATE}")
    parser.add_argument("--end-date", type=str, default=None, help="结束日期，默认为今天")
    parser.add_argument("--ts-codes", type=str, default=None, help="股票代码列表，逗号分隔（如 600000.SH,000001.SZ），不传则获取全部主板股票")
    parser.add_argument("--index-codes", type=str, default=None, help=f"指数代码列表，逗号分隔，默认 {','.join(DEFAULT_INDEX_CODES)}")
    parser.add_argument("--skip-stock-list", action="store_true", help="跳过股票列表获取")
    parser.add_argument("--skip-hsgt", action="store_true", help="跳过沪深港通股票列表")
    parser.add_argument("--skip-st", action="store_true", help="跳过 ST 股票列表")
    parser.add_argument("--skip-company", action="store_true", help="跳过公司基本信息")
    parser.add_argument("--skip-index-basic", action="store_true", help="跳过指数基础信息")
    parser.add_argument("--skip-index-weight", action="store_true", help="跳过指数成分权重")
    parser.add_argument("--skip-calendar", action="store_true", help="跳过交易日历")
    parser.add_argument("--skip-qfq-daily", action="store_true", help="跳过日线行情")
    parser.add_argument("--skip-daily-basic", action="store_true", help="跳过每日指标")
    parser.add_argument("--skip-adj-factor", action="store_true", help="跳过复权因子")
    parser.add_argument("--skip-financial", action="store_true", help="跳过财务报表")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # 验证环境
    try:
        import tushare  # noqa: F401
        get_tushare_pro()
    except ModuleNotFoundError:
        raise SystemExit("未检测到 tushare，请先安装: pip install tushare")
    except ValueError as e:
        raise SystemExit(str(e))

    output_dir = Path(args.output_dir)
    start_date = args.start_date
    end_date = args.end_date or get_default_fetch_end_date()

    # 获取指数代码列表
    if args.index_codes:
        index_codes = [code.strip() for code in args.index_codes.split(",")]
    else:
        index_codes = DEFAULT_INDEX_CODES

    print("=" * 60)
    print("数据获取任务")
    print("=" * 60)
    print(f"输出目录: {output_dir}")
    print(f"日期范围: {start_date} - {end_date}")
    print(f"指数代码: {index_codes}")
    print("=" * 60)

    try:
        # 基础数据（不依赖股票代码列表）
        if not args.skip_stock_list:
            fetch_stock_list(output_dir, end_date)

        if not args.skip_hsgt:
            fetch_stock_hsgt(output_dir, end_date, start_date)

        if not args.skip_st:
            fetch_stock_st(output_dir, end_date)

        if not args.skip_company:
            fetch_company_basic_info(output_dir, end_date)

        if not args.skip_index_basic:
            fetch_index_basic(output_dir, end_date)

        if not args.skip_index_weight:
            fetch_index_weight(output_dir, end_date, index_codes)

        if not args.skip_calendar:
            fetch_trade_calendar(output_dir, end_date, start_date)

        # 获取股票代码列表
        if args.ts_codes:
            ts_codes = [code.strip() for code in args.ts_codes.split(",")]
        else:
            # 实时获取所有主板股票代码
            ts_codes = get_all_stock_codes()

        if ts_codes:
            print(f"\n将获取以下 {len(ts_codes)} 只股票的数据:")
            print(f"  {', '.join(ts_codes[:10])}{'...' if len(ts_codes) > 10 else ''}")

            # 行情数据
            if not args.skip_qfq_daily:
                fetch_qfq_daily(output_dir, end_date, ts_codes, start_date, end_date)

            if not args.skip_daily_basic:
                fetch_daily_basic(output_dir, end_date, ts_codes, start_date, end_date)

            if not args.skip_adj_factor:
                fetch_adj_factor(output_dir, end_date, ts_codes, start_date, end_date)

            # 财务报表
            if not args.skip_financial:
                fetch_financial_statements(output_dir, end_date, ts_codes, start_date, end_date)
        else:
            print("\n没有指定股票代码，跳过个股数据获取")

        print("=" * 60)
        print("数据获取完成")
        print("=" * 60)

    except Exception as e:
        raise SystemExit(f"数据获取失败: {e}")


if __name__ == "__main__":
    main()
