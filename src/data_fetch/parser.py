import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="数据获取: 获取并分类保存市场数据")
    common_group = parser.add_argument_group("通用参数")
    common_group.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help='输出根目录，默认 "data"',
    )
    common_group.add_argument(
        "--skip-financial",
        action="store_true",
        help="跳过公司财报抓取（默认不跳过）",
    )
    common_group.add_argument(
        "--skip-qfq-daily",
        action="store_true",
        help="跳过A股前复权日线行情抓取（默认不跳过）",
    )
    common_group.add_argument(
        "--skip-qfq-5min",
        action="store_true",
        help="跳过A股前复权5分钟行情抓取（默认不跳过）",
    )
    common_group.add_argument(
        "--skip-daily-basic",
        action="store_true",
        help="跳过A股每日指标（daily_basic）抓取（默认不跳过）",
    )
    common_group.add_argument(
        "--skip-adj-factor",
        action="store_true",
        help="跳过A股复权因子（adj_factor）抓取（默认不跳过）",
    )
    return parser
