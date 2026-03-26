from __future__ import annotations

import csv
from pathlib import Path


def find_single_file(base_dir: Path, pattern: str, hint: str) -> Path:
    files = sorted(base_dir.rglob(pattern))
    if not files:
        raise FileNotFoundError(f"未找到 {hint}，查找路径: {base_dir}/{pattern}")
    return files[0]


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        if reader.fieldnames is None:
            raise ValueError(f"CSV 头部为空: {csv_path}")
        normalized_rows: list[dict[str, str]] = []
        for row in reader:
            normalized_row: dict[str, str] = {}
            for key, value in row.items():
                if key is None:
                    continue
                normalized_key = key.lstrip("\ufeff").strip()
                normalized_row[normalized_key] = (value or "").strip()
            normalized_rows.append(normalized_row)
        return normalized_rows

