from __future__ import annotations

import csv
from pathlib import Path


def open_workbook(xls_path: Path):
    try:
        import xlrd  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit("未安装 xlrd，无法读取 .xls。请先执行: pip install xlrd") from exc
    return xlrd.open_workbook(str(xls_path))


def cell_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def convert_xls_to_csv(
    *,
    xls_path: Path,
    output_csv: Path | None = None,
    sheet_name: str | None = None,
    sheet_index: int = 0,
) -> tuple[Path, str, int]:
    if not xls_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {xls_path}")

    out_csv = output_csv or xls_path.with_suffix(".csv")
    workbook = open_workbook(xls_path)
    sheet = workbook.sheet_by_name(sheet_name) if sheet_name else workbook.sheet_by_index(sheet_index)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp)
        for row_idx in range(sheet.nrows):
            row_values = [cell_to_text(cell) for cell in sheet.row_values(row_idx)]
            writer.writerow(row_values)

    return out_csv, sheet.name, sheet.nrows

