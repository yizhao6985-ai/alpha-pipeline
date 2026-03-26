from __future__ import annotations

from pathlib import Path

from ..path_manager import (
    build_stock_hsgt_list_path,
    build_stock_list_path,
    build_stock_st_list_path,
    has_current_data,
)
from ..runtime import (
    get_default_index_basic_markets,
    get_default_index_codes,
    get_default_stock_index_basic_categories,
    get_runtime_ts_codes,
    write_runtime_targets,
)
from .common import DataFetchError, EmptyDataError, write_csv


def fetch_stock_base_datasets(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    start_date: str,
) -> None:
    hsgt_stock_list_path = build_stock_hsgt_list_path(
        base_dir=output_dir,
        today_ymd=today_ymd,
        start_date=start_date,
        end_date=today_ymd,
    )
    if has_current_data(hsgt_stock_list_path):
        print(f"已存在，跳过沪深港通股票列表: {hsgt_stock_list_path}")
    else:
        print("正在获取沪深港通股票列表...")
        try:
            hsgt_stock_list_df = fetcher.fetch_stock_hsgt_list(update_date=today_ymd).data
        except Exception as exc:
            raise DataFetchError(f"沪深港通股票列表获取失败: {exc!r}") from exc
        if hsgt_stock_list_df is None or hsgt_stock_list_df.empty:
            raise EmptyDataError(f"stock_hsgt_list 数据为空（update_date={today_ymd}）")
        write_csv(hsgt_stock_list_df, hsgt_stock_list_path)
        print(f"- 沪深港通股票列表记录数: {len(hsgt_stock_list_df)}，更新日期: {today_ymd}\n  已保存: {hsgt_stock_list_path}")

    sh_path = build_stock_list_path(base_dir=output_dir, today_ymd=today_ymd, exchange="SSE")
    sz_path = build_stock_list_path(base_dir=output_dir, today_ymd=today_ymd, exchange="SZSE")
    if has_current_data(sh_path) and has_current_data(sz_path):
        print(f"已存在，跳过股票列表: {sh_path} / {sz_path}")
    else:
        print("正在获取股票列表...")
        try:
            stock_list = fetcher.fetch_stock_list(update_date=today_ymd).data
        except Exception as exc:
            raise DataFetchError(f"股票列表获取失败: {exc!r}") from exc
        sh_df = stock_list["sh"]
        sz_df = stock_list["sz"]
        if sh_df is None or sh_df.empty:
            raise EmptyDataError(f"SSE stock_list 数据为空（update_date={today_ymd}）")
        if sz_df is None or sz_df.empty:
            raise EmptyDataError(f"SZ stock_list 数据为空（update_date={today_ymd}）")
        if not has_current_data(sh_path):
            write_csv(sh_df, sh_path)
            print(f"- 上交所股票列表记录数: {len(sh_df)}，更新日期: {today_ymd}\n  已保存: {sh_path}")
        else:
            print(f"- 已存在，跳过上交所股票列表: {sh_path}")
        if not has_current_data(sz_path):
            write_csv(sz_df, sz_path)
            print(f"- 深交所股票列表记录数: {len(sz_df)}，更新日期: {today_ymd}\n  已保存: {sz_path}")
        else:
            print(f"- 已存在，跳过深交所股票列表: {sz_path}")

    st_path = build_stock_st_list_path(base_dir=output_dir, today_ymd=today_ymd)
    st_df = None
    if has_current_data(st_path):
        print(f"已存在，跳过 ST 股票列表: {st_path}")
    else:
        print("正在获取 ST 股票列表...")
        try:
            st_df = fetcher.fetch_st_stock_list(update_date=today_ymd).data
        except Exception as exc:
            raise DataFetchError(f"ST 股票列表获取失败: {exc!r}") from exc
        if st_df is None:
            raise DataFetchError(f"ST 股票列表为空（update_date={today_ymd}）")
        write_csv(st_df, st_path)
        print(f"- ST 股票列表记录数: {len(st_df)}，更新日期: {today_ymd}\n  已保存: {st_path}")

    # 抓取 ST 列表后，自动从 runtime ts_codes 中排除 ST 股票，避免后续公司级行情/财报误抓。
    runtime_ts_codes = list(get_runtime_ts_codes())
    if runtime_ts_codes and st_df is not None and "ts_code" in st_df.columns:
        st_ts_codes = set(st_df["ts_code"].dropna().astype(str).str.strip().str.upper().tolist())
        filtered_ts_codes = [code for code in runtime_ts_codes if code not in st_ts_codes]
        removed_count = len(runtime_ts_codes) - len(filtered_ts_codes)
        if removed_count > 0:
            runtime_path = write_runtime_targets(
                ts_codes=filtered_ts_codes,
                index_codes=get_default_index_codes(),
                index_basic_markets=get_default_index_basic_markets(),
                stock_index_basic_categories=get_default_stock_index_basic_categories(),
            )
            print(f"已从 runtime ts_codes 排除 ST 股票 {removed_count} 个: {runtime_path}")
