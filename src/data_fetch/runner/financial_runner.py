from __future__ import annotations

from pathlib import Path

from ..path_manager import build_financial_statement_path, has_current_data
from .common import DataFetchError, EmptyDataError, write_csv


def fetch_default_financial_statements(
    *,
    output_dir: Path,
    today_ymd: str,
    fetcher,
    ts_codes: tuple[str, ...],
    start_date: str,
    end_date: str,
) -> None:
    if not ts_codes:
        return
    print("检测到默认财报公司配置，将按默认日期范围 " f"{start_date} - {end_date} 获取财报: {', '.join(ts_codes)}")
    for ts_code in ts_codes:
        balancesheet_output_path = build_financial_statement_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            statement_type="balancesheet",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if has_current_data(balancesheet_output_path):
            print(f"已存在，跳过资产负债表: {ts_code}\n  文件: {balancesheet_output_path}")
        else:
            print(f"正在获取资产负债表: {ts_code} ...")
            try:
                balancesheet_df = fetcher.fetch_company_balancesheet(
                    ts_code=ts_code,
                    ann_date=None,
                    start_date=start_date,
                    end_date=end_date,
                    period=None,
                    report_type=None,
                    comp_type=None,
                    fields=None,
                ).data
            except Exception as exc:
                raise DataFetchError(f"资产负债表获取失败: {exc!r}") from exc
            if balancesheet_df is None or balancesheet_df.empty:
                raise EmptyDataError(f"balancesheet 数据为空（ts_code={ts_code}）")
            write_csv(balancesheet_df, balancesheet_output_path)
            print(f"- 资产负债表记录数: {len(balancesheet_df)}，股票: {ts_code}\n  已保存: {balancesheet_output_path}")

        income_output_path = build_financial_statement_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            statement_type="income",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if has_current_data(income_output_path):
            print(f"已存在，跳过利润表: {ts_code}\n  文件: {income_output_path}")
        else:
            print(f"正在获取利润表: {ts_code} ...")
            try:
                income_df = fetcher.fetch_company_income(
                    ts_code=ts_code,
                    ann_date=None,
                    f_ann_date=None,
                    start_date=start_date,
                    end_date=end_date,
                    period=None,
                    report_type=None,
                    comp_type=None,
                    fields=None,
                ).data
            except Exception as exc:
                raise DataFetchError(f"利润表获取失败: {exc!r}") from exc
            if income_df is None or income_df.empty:
                raise EmptyDataError(f"income 数据为空（ts_code={ts_code}）")
            write_csv(income_df, income_output_path)
            print(f"- 利润表记录数: {len(income_df)}，股票: {ts_code}\n  已保存: {income_output_path}")

        cashflow_output_path = build_financial_statement_path(
            base_dir=output_dir,
            today_ymd=today_ymd,
            statement_type="cashflow",
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
        )
        if has_current_data(cashflow_output_path):
            print(f"已存在，跳过现金流量表: {ts_code}\n  文件: {cashflow_output_path}")
        else:
            print(f"正在获取现金流量表: {ts_code} ...")
            try:
                cashflow_df = fetcher.fetch_company_cashflow(
                    ts_code=ts_code,
                    ann_date=None,
                    f_ann_date=None,
                    start_date=start_date,
                    end_date=end_date,
                    period=None,
                    report_type=None,
                    comp_type=None,
                    is_calc=None,
                    fields=None,
                ).data
            except Exception as exc:
                raise DataFetchError(f"现金流量表获取失败: {exc!r}") from exc
            if cashflow_df is None or cashflow_df.empty:
                raise EmptyDataError(f"cashflow 数据为空（ts_code={ts_code}）")
            write_csv(cashflow_df, cashflow_output_path)
            print(f"- 现金流量表记录数: {len(cashflow_df)}，股票: {ts_code}\n  已保存: {cashflow_output_path}")
