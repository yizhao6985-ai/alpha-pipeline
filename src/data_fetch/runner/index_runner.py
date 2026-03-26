from __future__ import annotations

from pathlib import Path

from ..path_manager import build_index_basic_path, build_index_weight_path
from ..runtime import (
    get_default_index_basic_markets,
    get_default_index_codes,
    get_default_stock_index_basic_categories,
    get_runtime_ts_codes,
    write_runtime_targets,
)
from ..sources.tushare.index_basic import filter_stock_index_basic
from .common import DataFetchError, EmptyDataError, write_csv


def fetch_stock_index_basic(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    index_basic_markets: tuple[str, ...],
) -> None:
    print("正在获取股票类指数基础信息...")
    try:
        index_basic_df = fetcher.fetch_market_index_basic().data
    except Exception as exc:
        raise DataFetchError(f"指数基础信息获取失败: {exc!r}") from exc
    if index_basic_df is None or index_basic_df.empty:
        raise EmptyDataError("market_index_basic 数据为空")
    stock_index_basic_df = filter_stock_index_basic(index_basic_df)
    if stock_index_basic_df.empty:
        raise EmptyDataError("market_index_basic 股票类指数数据为空")
    for market in index_basic_markets:
        market_df = stock_index_basic_df[stock_index_basic_df["market"] == market]
        if market_df.empty:
            print(f"- {market} 无股票类指数基础信息，跳过保存")
            continue
        for category, category_df in market_df.groupby("category", sort=True):
            category_name = str(category)
            output_path = build_index_basic_path(
                base_dir=output_dir,
                today_ymd=today_ymd,
                market=market,
                category=category_name,
            )
            write_csv(category_df.reset_index(drop=True), output_path)
            print(f"- {market}/{category_name} 股票类指数基础信息记录数: {len(category_df)}，已保存: {output_path}")


def fetch_default_index_weights(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    index_codes: tuple[str, ...],
) -> None:
    if not index_codes:
        return

    print("检测到默认指数代码配置，将获取全量指数成分和权重: " f"{', '.join(index_codes)}")
    collected_con_codes: list[str] = []

    for index_code in index_codes:
        output_path = build_index_weight_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            index_code=index_code,
        )
        print(f"正在获取指数成分和权重: {index_code} ...")
        try:
            index_weight_df = fetcher.fetch_market_index_weight(index_code=index_code).data
        except Exception as exc:
            raise DataFetchError(f"指数成分和权重获取失败: {exc!r}") from exc
        if index_weight_df is None or index_weight_df.empty:
            raise EmptyDataError(f"index_weight 数据为空（index_code={index_code}）")
        if "trade_date" not in index_weight_df.columns:
            raise DataFetchError(f"index_weight 缺少 trade_date 字段（index_code={index_code}）")

        latest_trade_date = index_weight_df["trade_date"].max()
        latest_df = index_weight_df[index_weight_df["trade_date"] == latest_trade_date].reset_index(drop=True)
        latest_codes = latest_df["con_code"].dropna().astype(str).str.strip().str.upper().tolist()
        collected_con_codes.extend(code for code in latest_codes if code)
        write_csv(latest_df, output_path)
        print(f"- 指数成分和权重记录数: {len(latest_df)}，指数: {index_code}，最新交易日: {latest_trade_date}\n  已保存: {output_path}")

    if collected_con_codes:
        merged_ts_codes: list[str] = list(get_runtime_ts_codes())
        seen_ts_codes = {code.upper() for code in merged_ts_codes}
        for con_code in collected_con_codes:
            if con_code not in seen_ts_codes:
                merged_ts_codes.append(con_code)
                seen_ts_codes.add(con_code)
        runtime_path = write_runtime_targets(
            ts_codes=merged_ts_codes,
            index_codes=get_default_index_codes(),
            index_basic_markets=get_default_index_basic_markets(),
            stock_index_basic_categories=get_default_stock_index_basic_categories(),
        )
        print(f"已同步指数成分股到 runtime ts_codes（共 {len(merged_ts_codes)} 个）: {runtime_path}")
