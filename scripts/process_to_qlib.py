#!/usr/bin/env python3
"""
数据处理脚本：将原始数据转换为 Qlib 格式

功能：
1. 排除 ST 股票
2. 合并行情、指标、筹码分布数据
3. 生成 Qlib 标准格式目录结构（bin 格式）

Qlib 目录结构：
    qlib_data/
    ├── calendars/
    │   └── day.txt          # 交易日历 (YYYY-MM-DD)
    ├── instruments/
    │   ├── all.txt          # 全部股票
    │   ├── csi300.txt       # 沪深300成分股
    │   ├── csi500.txt       # 中证500成分股
    │   └── csi1000.txt      # 中证1000成分股
    └── features/
        └── sh600000/         # 每只股票一个目录
            └── close.bin     # 每个字段一个 bin 文件
            └── close.meta    # 对应的 meta 文件

用法:
    python scripts/process_to_qlib.py
    python scripts/process_to_qlib.py --date 20260408
    python scripts/process_to_qlib.py --output-dir ~/.qlib/qlib_data/cn_data
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

# 添加 scripts 目录到路径
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fetchers.base import ensure_dir


# 指数代码映射
INDEX_CODES = {
    "csi300": "399300.SZ",    # 沪深300
    "csi500": "000905.SH",    # 中证500
    "csi100": "000903.SH",    # 中证100
    "csi1000": "000852.SH",   # 中证1000
    "csi_all": "000985.CSI",  # 中证全指
}

# Qlib bin 格式字段映射
QLIB_FIELD_NAMES = {
    "open": "$open",
    "high": "$high",
    "low": "$low",
    "close": "$close",
    "volume": "$volume",
    "money": "$money",
    "pre_close": "$pre_close",
    "change": "$change",
    "pct_chg": "$pct_chg",
    "adj_factor": "$adj_factor",
    "turnover_rate": "$turnover_rate",
    "turnover_rate_f": "$turnover_rate_f",
    "volume_ratio": "$volume_ratio",
    "pe": "$pe",
    "pe_ttm": "$pe_ttm",
    "pb": "$pb",
    "ps": "$ps",
    "ps_ttm": "$ps_ttm",
    "dv_ratio": "$dv_ratio",
    "dv_ttm": "$dv_ttm",
    "total_share": "$total_share",
    "float_share": "$float_share",
    "free_share": "$free_share",
    "total_mv": "$total_mv",
    "circ_mv": "$circ_mv",
    "his_low": "$his_low",
    "his_high": "$his_high",
    "cost_5pct": "$cost_5pct",
    "cost_15pct": "$cost_15pct",
    "cost_50pct": "$cost_50pct",
    "cost_85pct": "$cost_85pct",
    "cost_95pct": "$cost_95pct",
    "weight_avg": "$weight_avg",
    "winner_rate": "$winner_rate",
}


def find_latest_data_dir(data_root: Path) -> str:
    """找到最新的数据日期目录"""
    date_dirs = [d.name for d in data_root.iterdir() if d.is_dir() and d.name.isdigit() and len(d.name) == 8]
    if not date_dirs:
        raise ValueError(f"未找到数据目录: {data_root}")
    return max(date_dirs)


def load_st_list(data_dir: Path, date_str: str) -> set[str]:
    """加载 ST 股票列表"""
    st_dir = data_dir / date_str / "stock" / "st_stock_list"
    st_codes = set()
    
    if not st_dir.exists():
        return st_codes
    
    for csv_file in st_dir.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file, encoding="utf-8")
            if "ts_code" in df.columns:
                st_codes.update(df["ts_code"].astype(str).tolist())
        except Exception:
            continue
    
    return st_codes


def load_index_components(data_dir: Path, date_str: str) -> dict[str, set[str]]:
    """加载各指数成分股"""
    index_weight_dir = data_dir / date_str / "index" / "index_weight"
    components = {}
    
    if not index_weight_dir.exists():
        return components
    
    # 指数代码到文件名的映射
    index_file_map = {
        "csi300": "399300_SZ.csv",
        "csi500": "000905_SH.csv",
        "csi100": "000903_SH.csv",
        "csi1000": "000852_SH.csv",
        "csi_all": "000985_CSI.csv",
    }
    
    for index_name, filename in index_file_map.items():
        file_path = index_weight_dir / filename
        if file_path.exists():
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
                # 从 con_code 列获取成分股代码
                if "con_code" in df.columns:
                    components[index_name] = set(df["con_code"].astype(str).tolist())
            except Exception:
                continue
    
    return components


def get_qfq_files(data_dir: Path, date_str: str) -> list[Path]:
    """获取所有前复权日线文件列表"""
    qfq_dir = data_dir / date_str / "quote" / "qfq"
    if not qfq_dir.exists():
        return []
    return list(qfq_dir.glob("*.csv"))


def get_daily_basic_files(data_dir: Path, date_str: str) -> list[Path]:
    """获取所有每日指标文件列表"""
    db_dir = data_dir / date_str / "quote" / "basic"
    if not db_dir.exists():
        return []
    return list(db_dir.glob("*.csv"))


def get_cyq_files(data_dir: Path, date_str: str) -> list[Path]:
    """获取所有筹码分布文件列表"""
    cyq_dir = data_dir / date_str / "quote" / "cyq"
    if not cyq_dir.exists():
        return []
    return list(cyq_dir.glob("*.csv"))


def extract_ts_code_from_filename(filename: str) -> str | None:
    """从文件名提取股票代码"""
    name = filename.replace(".csv", "")
    if "_" in name:
        parts = name.rsplit("_", 1)
        if len(parts) == 2:
            return f"{parts[0]}.{parts[1]}"
    return None


def to_qlib_symbol(ts_code: str) -> str:
    """转换为 Qlib 股票代码格式: 600000.SH -> SH600000"""
    if "." in ts_code:
        code, exchange = ts_code.split(".")
        if exchange == "SH":
            return f"SH{code}"
        elif exchange == "SZ":
            return f"SZ{code}"
        elif exchange == "BJ":
            return f"BJ{code}"
        elif exchange == "CSI":
            return f"SH{code}"  # CSI 指数用 SH 前缀
    return ts_code


def to_feature_dir_name(qlib_symbol: str) -> str:
    """转换为 features 目录名: SH600000 -> sh600000"""
    return qlib_symbol.lower()


def format_date(date_str: str | int) -> str:
    """将日期格式化为 YYYY-MM-DD"""
    d = str(date_str)
    if len(d) == 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return d


def date_to_qlib_int(date_str: str) -> int:
    """将 YYYY-MM-DD 转换为 Qlib 内部使用的整数格式 YYYYMMDD"""
    return int(date_str.replace("-", ""))


def process_stock_data(
    qfq_file: Path,
    daily_basic_file: Path | None,
    cyq_file: Path | None,
    st_codes: set[str],
) -> pd.DataFrame | None:
    """处理单只股票数据，合并行情、指标和筹码分布"""
    ts_code = extract_ts_code_from_filename(qfq_file.name)
    if not ts_code:
        return None
    
    if ts_code in st_codes:
        return None
    
    try:
        # 读取行情数据
        qfq_df = pd.read_csv(qfq_file, encoding="utf-8")
        if qfq_df.empty:
            return None
        
        # 删除 ts_code 列
        if "ts_code" in qfq_df.columns:
            qfq_df = qfq_df.drop(columns=["ts_code"])
        
        # 标准化列名并格式化日期
        qfq_df = qfq_df.rename(columns={
            "trade_date": "date",
            "vol": "volume",
            "amount": "money",
        })
        qfq_df["date"] = qfq_df["date"].apply(format_date)
        
        # 确保必要的列存在
        required_cols = ["date", "open", "high", "low", "close", "volume", "money"]
        for col in required_cols:
            if col not in qfq_df.columns:
                return None
        
        # 合并每日指标数据
        if daily_basic_file and daily_basic_file.exists():
            try:
                db_df = pd.read_csv(daily_basic_file, encoding="utf-8")
                if not db_df.empty:
                    db_df = db_df.rename(columns={"trade_date": "date"})
                    db_df["date"] = db_df["date"].apply(format_date)
                    if "ts_code" in db_df.columns:
                        db_df = db_df.drop(columns=["ts_code"])
                    indicator_cols = ["date", "turnover_rate", "turnover_rate_f", 
                                     "volume_ratio", "pe", "pe_ttm", "pb", "ps", 
                                     "ps_ttm", "dv_ratio", "dv_ttm", "total_share",
                                     "float_share", "free_share", "total_mv", "circ_mv"]
                    available_cols = [c for c in indicator_cols if c in db_df.columns]
                    if available_cols:
                        db_df = db_df[available_cols]
                        qfq_df = qfq_df.merge(db_df, on="date", how="left")
            except Exception:
                pass
        
        # 合并筹码分布数据
        if cyq_file and cyq_file.exists():
            try:
                cyq_df = pd.read_csv(cyq_file, encoding="utf-8")
                if not cyq_df.empty:
                    cyq_df = cyq_df.rename(columns={"trade_date": "date"})
                    cyq_df["date"] = cyq_df["date"].apply(format_date)
                    if "ts_code" in cyq_df.columns:
                        cyq_df = cyq_df.drop(columns=["ts_code"])
                    cyq_cols = ["date", "his_low", "his_high", "cost_5pct", "cost_15pct",
                               "cost_50pct", "cost_85pct", "cost_95pct", "weight_avg", "winner_rate"]
                    available_cyq_cols = [c for c in cyq_cols if c in cyq_df.columns]
                    if available_cyq_cols:
                        cyq_df = cyq_df[available_cyq_cols]
                        qfq_df = qfq_df.merge(cyq_df, on="date", how="left")
            except Exception:
                pass
        
        return qfq_df
    
    except Exception:
        return None


def process_all_data(
    data_dir: Path,
    date_str: str,
    st_codes: set[str],
) -> dict[str, pd.DataFrame]:
    """处理所有股票数据，返回以 qlib_symbol 为 key 的字典"""
    qfq_files = get_qfq_files(data_dir, date_str)
    
    if not qfq_files:
        raise ValueError(f"未找到行情数据: {data_dir / date_str / 'quote' / 'qfq'}")
    
    print(f"找到 {len(qfq_files)} 只股票数据，正在处理...")
    
    # 构建文件映射
    db_dir = data_dir / date_str / "quote" / "basic"
    db_file_map = {}
    if db_dir.exists():
        for f in db_dir.glob("*.csv"):
            ts_code = extract_ts_code_from_filename(f.name)
            if ts_code:
                db_file_map[ts_code] = f
    
    cyq_dir = data_dir / date_str / "quote" / "cyq"
    cyq_file_map = {}
    if cyq_dir.exists():
        for f in cyq_dir.glob("*.csv"):
            ts_code = extract_ts_code_from_filename(f.name)
            if ts_code:
                cyq_file_map[ts_code] = f
    
    print(f"  - 每日指标数据: {len(db_file_map)} 只")
    print(f"  - 筹码分布数据: {len(cyq_file_map)} 只")
    
    # 处理每只股票
    stock_data = {}
    skipped_st = 0
    
    for qfq_file in tqdm(qfq_files, desc="处理股票"):
        ts_code = extract_ts_code_from_filename(qfq_file.name)
        if not ts_code:
            continue
        
        if ts_code in st_codes:
            skipped_st += 1
            continue
        
        db_file = db_file_map.get(ts_code)
        cyq_file = cyq_file_map.get(ts_code)
        df = process_stock_data(qfq_file, db_file, cyq_file, st_codes)
        
        if df is not None and not df.empty:
            qlib_symbol = to_qlib_symbol(ts_code)
            stock_data[qlib_symbol] = df
    
    if skipped_st > 0:
        print(f"已排除 {skipped_st} 只 ST 股票")
    
    if not stock_data:
        raise ValueError("没有有效的数据")
    
    return stock_data


def save_csv_raw(stock_data: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """保存每只股票的 CSV 到 csv_raw 目录（中间数据）"""
    csv_dir = output_dir / "csv_raw"
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    for qlib_symbol, df in tqdm(stock_data.items(), desc="保存 CSV"):
        # 创建股票目录 (使用小写的 qlib_symbol，如 sh600000)
        stock_dir = csv_dir / to_feature_dir_name(qlib_symbol)
        stock_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 CSV
        csv_path = stock_dir / "data.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8")
    
    print(f"已保存 {len(stock_data)} 只股票的 CSV 文件到: {csv_dir}")


def convert_to_bin(stock_data: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """将数据转换为 Qlib bin 格式并保存到 features 目录
    
    官方 Qlib 格式: {field}.day.bin (如 close.day.bin, open.day.bin)
    """
    features_dir = output_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    
    # 字段名映射到官方 Qlib 格式（去掉 $ 前缀）
    field_name_map = {
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume",
        "money": "money",
        "pre_close": "pre_close",
        "change": "change",
        "pct_chg": "pct_chg",
        "adj_factor": "factor",  # 官方使用 factor 而不是 adj_factor
        "turnover_rate": "turnover_rate",
        "turnover_rate_f": "turnover_rate_f",
        "volume_ratio": "volume_ratio",
        "pe": "pe",
        "pe_ttm": "pe_ttm",
        "pb": "pb",
        "ps": "ps",
        "ps_ttm": "ps_ttm",
        "dv_ratio": "dv_ratio",
        "dv_ttm": "dv_ttm",
        "total_share": "total_share",
        "float_share": "float_share",
        "free_share": "free_share",
        "total_mv": "total_mv",
        "circ_mv": "circ_mv",
        "his_low": "his_low",
        "his_high": "his_high",
        "cost_5pct": "cost_5pct",
        "cost_15pct": "cost_15pct",
        "cost_50pct": "cost_50pct",
        "cost_85pct": "cost_85pct",
        "cost_95pct": "cost_95pct",
        "weight_avg": "weight_avg",
        "winner_rate": "winner_rate",
    }
    
    # 按股票转换
    for qlib_symbol, df in tqdm(stock_data.items(), desc="转换为 bin"):
        # 创建股票目录
        stock_dir = features_dir / to_feature_dir_name(qlib_symbol)
        stock_dir.mkdir(parents=True, exist_ok=True)
        
        # 将日期转换为整数
        df = df.copy()
        df["date_int"] = df["date"].apply(date_to_qlib_int)
        df = df.sort_values("date_int")
        
        # 为每个字段创建 bin 文件
        for field in df.columns:
            if field in ("date", "date_int"):
                continue
            
            # 使用官方格式的字段名
            qlib_field = field_name_map.get(field, field)
            bin_path = stock_dir / f"{qlib_field}.day.bin"
            
            # 获取有效数据（非 NaN）
            valid_data = df[["date_int", field]].dropna()
            if valid_data.empty:
                continue
            
            dates = valid_data["date_int"].values.astype(np.int64)
            values = valid_data[field].values.astype(np.float32)
            
            # 写入 bin 文件
            # Qlib bin 格式: [date1, value1, date2, value2, ...]
            data_array = np.column_stack([dates, values]).flatten()
            data_array.astype(np.float32).tofile(bin_path)
    
    print(f"已转换 {len(stock_data)} 只股票的 bin 文件到: {features_dir}")


def save_instruments(
    stock_data: dict[str, pd.DataFrame],
    output_dir: Path,
    index_components: dict[str, set[str]],
) -> None:
    """保存 instruments 文件"""
    instruments_dir = output_dir / "instruments"
    instruments_dir.mkdir(parents=True, exist_ok=True)
    
    # 准备所有股票的数据范围
    stock_ranges = {}
    for qlib_symbol, df in stock_data.items():
        dates = sorted(df["date"].tolist())
        stock_ranges[qlib_symbol] = (dates[0], dates[-1])
    
    # 保存 all.txt
    all_path = instruments_dir / "all.txt"
    with open(all_path, "w", encoding="utf-8") as f:
        for symbol in sorted(stock_ranges.keys()):
            start, end = stock_ranges[symbol]
            f.write(f"{symbol}\t{start}\t{end}\n")
    print(f"已保存: {all_path} ({len(stock_ranges)} 只)")
    
    # 保存各指数成分股 instruments
    for index_name, components in index_components.items():
        index_path = instruments_dir / f"{index_name}.txt"
        index_stocks = set()
        
        with open(index_path, "w", encoding="utf-8") as f:
            for ts_code in sorted(components):
                qlib_symbol = to_qlib_symbol(ts_code)
                if qlib_symbol in stock_ranges:
                    start, end = stock_ranges[qlib_symbol]
                    f.write(f"{qlib_symbol}\t{start}\t{end}\n")
                    index_stocks.add(qlib_symbol)
        
        print(f"已保存: {index_path} ({len(index_stocks)} 只)")


def save_calendars(stock_data: dict[str, pd.DataFrame], output_dir: Path) -> None:
    """保存交易日历"""
    # 收集所有日期
    all_dates = set()
    for df in stock_data.values():
        all_dates.update(df["date"].tolist())
    
    dates = sorted(all_dates)
    
    calendars_dir = output_dir / "calendars"
    calendars_dir.mkdir(parents=True, exist_ok=True)
    
    calendar_path = calendars_dir / "day.txt"
    with open(calendar_path, "w", encoding="utf-8") as f:
        for d in dates:
            f.write(f"{d}\n")
    
    print(f"已保存: {calendar_path} ({len(dates)} 个交易日)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="处理数据并生成 Qlib 格式")
    parser.add_argument("--data-dir", type=str, default="data", help="原始数据目录，默认 data")
    parser.add_argument("--date", type=str, default=None, help="数据日期（如 20260408），默认使用最新日期")
    parser.add_argument("--output-dir", type=str, default="qlib_data", help="输出目录，默认 qlib_data")
    parser.add_argument("--skip-bin", action="store_true", help="跳过 bin 转换，只保存 CSV")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    # 确定数据日期
    if args.date:
        date_str = args.date
    else:
        date_str = find_latest_data_dir(data_dir)
    
    print("=" * 60)
    print("Qlib 数据处理任务")
    print("=" * 60)
    print(f"数据日期: {date_str}")
    print(f"数据来源: {data_dir / date_str}")
    print(f"输出目录: {output_dir}")
    print("=" * 60)
    
    # 加载 ST 股票列表
    print("\n正在加载 ST 股票列表...")
    st_codes = load_st_list(data_dir, date_str)
    print(f"ST 股票数量: {len(st_codes)}")
    
    # 加载指数成分股
    print("\n正在加载指数成分股...")
    index_components = load_index_components(data_dir, date_str)
    for name, codes in index_components.items():
        print(f"  - {name}: {len(codes)} 只")
    
    # 处理数据
    print("\n正在处理股票数据...")
    stock_data = process_all_data(data_dir, date_str, st_codes)
    print(f"有效股票数量: {len(stock_data)}")
    
    # 保存 CSV 原始数据（中间数据）
    print("\n正在保存 CSV 原始数据...")
    save_csv_raw(stock_data, output_dir)
    
    # 转换为 bin 格式
    if not args.skip_bin:
        print("\n正在转换为 bin 格式...")
        convert_to_bin(stock_data, output_dir)
    
    # 保存 instruments
    print("\n正在保存 instruments...")
    save_instruments(stock_data, output_dir, index_components)
    
    # 保存 calendars
    print("\n正在保存 calendars...")
    save_calendars(stock_data, output_dir)
    
    print("\n" + "=" * 60)
    print("数据处理完成")
    print("=" * 60)
    print(f"\n生成的目录结构:")
    print(f"  {output_dir}/")
    print(f"  ├── calendars/day.txt")
    print(f"  ├── instruments/all.txt")
    print(f"  ├── instruments/csi300.txt")
    print(f"  ├── csv_raw/sh600000/data.csv")
    print(f"  └── features/sh600000/close.bin")
    print(f"      ...")


if __name__ == "__main__":
    main()
