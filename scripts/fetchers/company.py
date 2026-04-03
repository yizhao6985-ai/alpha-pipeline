"""
公司相关数据获取
"""

from __future__ import annotations

from pathlib import Path

from .base import get_tushare_pro, save_csv, file_exists_and_not_empty


def fetch_company_basic_info(output_dir: Path, today_ymd: str) -> None:
    """获取公司基本信息"""
    pro = get_tushare_pro()

    # 上交所
    sh_path = output_dir / today_ymd / "company" / "company_basic_info" / f"company_basic_info_sh_{today_ymd}.csv"
    if file_exists_and_not_empty(sh_path):
        print(f"已存在，跳过: {sh_path}")
    else:
        print("正在获取上交所公司基本信息...")
        sh_df = pro.query("stock_company", exchange="SSE")
        save_csv(sh_df, sh_path)
        print(f"- 上交所公司信息: {len(sh_df)} 条")

    # 深交所
    sz_path = output_dir / today_ymd / "company" / "company_basic_info" / f"company_basic_info_sz_{today_ymd}.csv"
    if file_exists_and_not_empty(sz_path):
        print(f"已存在，跳过: {sz_path}")
    else:
        print("正在获取深交所公司基本信息...")
        sz_df = pro.query("stock_company", exchange="SZSE")
        save_csv(sz_df, sz_path)
        print(f"- 深交所公司信息: {len(sz_df)} 条")


def fetch_financial_statements(
    output_dir: Path,
    today_ymd: str,
    ts_codes: list[str],
    start_date: str,
    end_date: str,
) -> None:
    """获取财务报表（资产负债表、利润表、现金流量表）"""
    if not ts_codes:
        return

    pro = get_tushare_pro()
    print(f"正在获取 {len(ts_codes)} 只股票的财务报表...")

    for ts_code in ts_codes:
        # 资产负债表
        bs_path = (
            output_dir
            / today_ymd
            / "company"
            / "financial"
            / "balancesheet"
            / f"balancesheet_{ts_code.replace('.', '_')}_{start_date}_{end_date}.csv"
        )
        if file_exists_and_not_empty(bs_path):
            print(f"  已存在，跳过资产负债表 {ts_code}")
        else:
            df = pro.balancesheet(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                save_csv(df, bs_path)
                print(f"- 资产负债表 {ts_code}: {len(df)} 条")

        # 利润表
        inc_path = (
            output_dir
            / today_ymd
            / "company"
            / "financial"
            / "income"
            / f"income_{ts_code.replace('.', '_')}_{start_date}_{end_date}.csv"
        )
        if file_exists_and_not_empty(inc_path):
            print(f"  已存在，跳过利润表 {ts_code}")
        else:
            df = pro.income(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                save_csv(df, inc_path)
                print(f"- 利润表 {ts_code}: {len(df)} 条")

        # 现金流量表
        cf_path = (
            output_dir
            / today_ymd
            / "company"
            / "financial"
            / "cashflow"
            / f"cashflow_{ts_code.replace('.', '_')}_{start_date}_{end_date}.csv"
        )
        if file_exists_and_not_empty(cf_path):
            print(f"  已存在，跳过现金流量表 {ts_code}")
        else:
            df = pro.cashflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is not None and not df.empty:
                save_csv(df, cf_path)
                print(f"- 现金流量表 {ts_code}: {len(df)} 条")
