from __future__ import annotations

from pathlib import Path

from ..path_manager import build_company_basic_info_path, has_current_data
from .common import DataFetchError, EmptyDataError, write_csv


def fetch_company_basic_info(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
) -> None:
    sh_company_path = build_company_basic_info_path(base_dir=output_dir, today_ymd=today_ymd, exchange="SSE")
    sz_company_path = build_company_basic_info_path(base_dir=output_dir, today_ymd=today_ymd, exchange="SZSE")
    if has_current_data(sh_company_path) and has_current_data(sz_company_path):
        print(f"已存在，跳过上市公司基本信息: {sh_company_path} / {sz_company_path}")
        return
    print("正在获取上市公司基本信息...")
    try:
        company_basic_info = fetcher.fetch_company_basic_info(update_date=today_ymd).data
    except Exception as exc:
        raise DataFetchError(f"上市公司基本信息获取失败: {exc!r}") from exc
    sh_company_df = company_basic_info["sh"]
    sz_company_df = company_basic_info["sz"]
    if sh_company_df is None or sh_company_df.empty:
        raise EmptyDataError(f"SSE company_basic_info 数据为空（update_date={today_ymd}）")
    if sz_company_df is None or sz_company_df.empty:
        raise EmptyDataError(f"SZ company_basic_info 数据为空（update_date={today_ymd}）")
    if not has_current_data(sh_company_path):
        write_csv(sh_company_df, sh_company_path)
        print(f"- 上交所上市公司基本信息记录数: {len(sh_company_df)}，更新日期: {today_ymd}\n  已保存: {sh_company_path}")
    else:
        print(f"- 已存在，跳过上交所上市公司基本信息: {sh_company_path}")
    if not has_current_data(sz_company_path):
        write_csv(sz_company_df, sz_company_path)
        print(f"- 深交所上市公司基本信息记录数: {len(sz_company_df)}，更新日期: {today_ymd}\n  已保存: {sz_company_path}")
    else:
        print(f"- 已存在，跳过深交所上市公司基本信息: {sz_company_path}")
