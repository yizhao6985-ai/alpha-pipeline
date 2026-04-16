#!/usr/bin/env python3
"""
原始行情 CSV → Qlib 数据目录（``python -m scripts.build_qlib.to_qlib``；可选 ``scripts/process_to_qlib.py``）。

功能：
1. 排除 ST 股票
2. 合并行情 + 筹码 + **Tushare daily_basic**（`quote/basic/*.csv`：PE/PB/换手/市值等）
3. 通过同目录 `dump_bin.py` 生成 `features/*.day.bin` 等标准目录

筹码表保留字段 ``weight_avg``（非 VWAP）。``vwap_approx = (high+low+close)/3`` 为典型价近似；
另写入 ``vwap``（与 ``vwap_approx`` 相同数值）供 Qlib Alpha158 的 ``$vwap`` 表达式使用。
输出宽表不包含 ``pre_close``（昨收可用 ``Ref($close, 1)``）。

`calendars/day.txt` 使用 `dump_bin.write_calendars`；`instruments/*.txt` 均使用
`DumpDataBase.save_instruments`（含 `all.txt`、`index_all.txt`、各 `csi*.txt`）。

Qlib 目录结构（节选）：
    qlib_data/
    ├── calendars/day.txt
    ├── instruments/…
    ├── features/sh600000/*.day.bin
    └── csv_raw/…              # 处理过程中的宽表 CSV

用法:
    python -m scripts.build_qlib.to_qlib
    python scripts/process_to_qlib.py
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from scripts.build_qlib.dump_bin import DumpDataAll, make_process_bin_writer, write_calendars


# 指数代码映射
INDEX_CODES = {
    "csi300": "399300.SZ",    # 沪深300
    "csi500": "000905.SH",    # 中证500
    "csi100": "000903.SH",    # 中证100
    "csi1000": "000852.SH",   # 中证1000
    "csi_all": "000985.CSI",  # 中证全指
    "csi_a500": "000510.CSI",  # 中证A500
}

# 股票列名 → Qlib 特征名（与 Alpha 数据集等惯例一致：成交额为 money）
STOCK_BIN_RENAMES: dict[str, str] = {
    "amount": "money",
}

# daily_basic 并入宽表 / bin 的字段（与 Tushare 列名一致，供 Qlib 表达式 $pe、$pb 等）
DAILY_BASIC_COLS: tuple[str, ...] = (
    "pe",
    "pe_ttm",
    "pb",
    "ps",
    "ps_ttm",
    "turnover_rate",
    "volume_ratio",
    "circ_mv",
    "total_mv",
    "dv_ratio",
)


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
        "csi_a500": "000510_CSI.csv",
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


def get_cyq_files(data_dir: Path, date_str: str) -> list[Path]:
    """获取所有筹码分布文件列表"""
    cyq_dir = data_dir / date_str / "quote" / "cyq"
    if not cyq_dir.exists():
        return []
    return list(cyq_dir.glob("*.csv"))


def get_basic_files(data_dir: Path, date_str: str) -> list[Path]:
    """获取 daily_basic 每日指标文件列表（与 fetch_daily_basic 落盘路径一致）。"""
    basic_dir = data_dir / date_str / "quote" / "basic"
    if not basic_dir.exists():
        return []
    return list(basic_dir.glob("*.csv"))


def get_index_daily_files(data_dir: Path, date_str: str) -> list[Path]:
    """获取所有指数日线文件列表"""
    index_dir = data_dir / date_str / "index" / "index_daily"
    if not index_dir.exists():
        return []
    return list(index_dir.glob("*.csv"))


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


def _merge_daily_basic(qfq_df: pd.DataFrame, basic_file: Path | None) -> pd.DataFrame:
    """按交易日左连接 daily_basic；无文件或失败则原样返回。"""
    if basic_file is None or not basic_file.exists():
        return qfq_df
    try:
        b = pd.read_csv(basic_file, encoding="utf-8")
        if b.empty or "trade_date" not in b.columns:
            return qfq_df
        b = b.rename(columns={"trade_date": "date"})
        b["date"] = b["date"].apply(format_date)
        if "ts_code" in b.columns:
            b = b.drop(columns=["ts_code"])
        take = [c for c in DAILY_BASIC_COLS if c in b.columns]
        if not take:
            return qfq_df
        b = b[["date"] + take].copy()
        for c in take:
            b[c] = pd.to_numeric(b[c], errors="coerce")
        b = b.drop_duplicates(subset=["date"], keep="last").sort_values("date")
        return qfq_df.merge(b, on="date", how="left")
    except Exception:
        return qfq_df


def process_stock_data(
    qfq_file: Path,
    cyq_file: Path | None,
    st_codes: set[str] | frozenset[str],
    basic_file: Path | None = None,
) -> pd.DataFrame | None:
    """处理单只股票：前复权行情 + 筹码 + daily_basic（可选）。"""
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
            "amount": "amount",
        })
        qfq_df["date"] = qfq_df["date"].apply(format_date)

        # 前复权行情不需要复权因子列；旧 CSV 若含则去掉，避免写入 bin/features
        for _drop in ("adj_factor",):
            if _drop in qfq_df.columns:
                qfq_df = qfq_df.drop(columns=[_drop])
        
        # 确保必要的列存在
        required_cols = ["date", "open", "high", "low", "close", "volume", "amount"]
        for col in required_cols:
            if col not in qfq_df.columns:
                return None

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

        qfq_df = _merge_daily_basic(qfq_df, basic_file)

        # 与 Qlib 日历 /特征一致：日期升序（旧 → 新），Tushare 原始 CSV 多为降序
        qfq_df = qfq_df.sort_values("date", ascending=True).reset_index(drop=True)
        # 昨收可由 Ref($close, 1) 得到，不落盘
        if "pre_close" in qfq_df.columns:
            qfq_df = qfq_df.drop(columns=["pre_close"])

        qfq_df = _add_vwap_typical_price(qfq_df)

        return qfq_df

    except Exception:
        return None


def process_index_data(index_daily_file: Path) -> pd.DataFrame | None:
    """处理单个指数的日线行情数据
    
    index_daily 返回字段：
    - ts_code: 指数代码
    - trade_date: 交易日期
    - close: 收盘点位
    - open: 开盘点位
    - high: 最高点位
    - low: 最低点位
    - change: 涨跌点
    - pct_chg: 涨跌幅(%)
    - vol: 成交量（手）
    - amount: 成交额（千元）
    """
    if not index_daily_file.exists():
        return None
    
    try:
        df = pd.read_csv(index_daily_file, encoding="utf-8")
        if df.empty:
            return None
        
        # 删除 ts_code 列（从文件名获取）
        if "ts_code" in df.columns:
            df = df.drop(columns=["ts_code"])
        
        # 标准化列名
        df = df.rename(columns={
            "trade_date": "date",
            "vol": "volume",
            "amount": "amount",
        })
        df["date"] = df["date"].apply(format_date)

        df = df.sort_values("date", ascending=True).reset_index(drop=True)
        if "pre_close" in df.columns:
            df = df.drop(columns=["pre_close"])

        df = _add_vwap_typical_price(df)

        return df

    except Exception:
        return None


def _add_vwap_typical_price(df: pd.DataFrame) -> pd.DataFrame:
    """典型价近似 VWAP：``(high+low+close)/3``；``vwap`` 与 ``vwap_approx`` 同值供 ``$vwap`` 使用。"""
    if not all(c in df.columns for c in ("high", "low", "close")):
        return df
    out = df.copy()
    h = pd.to_numeric(out["high"], errors="coerce")
    l = pd.to_numeric(out["low"], errors="coerce")
    c = pd.to_numeric(out["close"], errors="coerce")
    out["vwap_approx"] = (h + l + c) / 3.0
    out["vwap"] = out["vwap_approx"]
    return out


def _process_one_stock_worker(
    qfq_file: str,
    cyq_file: str | None,
    basic_file: str | None,
    st_codes: frozenset[str],
) -> tuple[str, pd.DataFrame] | None:
    """并行任务：处理单只股票，返回 (qlib_symbol, DataFrame)。"""
    qfq_path = Path(qfq_file)
    ts_code = extract_ts_code_from_filename(qfq_path.name)
    if not ts_code or ts_code in st_codes:
        return None
    df = process_stock_data(
        qfq_path,
        Path(cyq_file) if cyq_file else None,
        st_codes,
        Path(basic_file) if basic_file else None,
    )
    if df is None or df.empty:
        return None
    return (to_qlib_symbol(ts_code), df)


def _process_one_index_worker(index_daily_file: str) -> tuple[str, pd.DataFrame] | None:
    """并行任务：处理单个指数 CSV。"""
    path = Path(index_daily_file)
    ts_code = extract_ts_code_from_filename(path.name)
    if not ts_code:
        return None
    df = process_index_data(path)
    if df is None or df.empty:
        return None
    return (to_qlib_symbol(ts_code), df)


def _save_one_csv(
    qlib_symbol: str,
    df: pd.DataFrame,
    csv_dir: Path,
    calendars_list: list[str] | None = None,
    csv_full_calendar: bool = True,
) -> None:
    """写入单个 csv_raw。默认与 ``day.txt`` 同一区间：从全局日历首日至末日 reindex，上市前/无行情日为 NaN。"""
    sub = csv_dir / to_feature_dir_name(qlib_symbol)
    sub.mkdir(parents=True, exist_ok=True)
    to_write = (
        _align_df_to_calendar(df, calendars_list, full_calendar=csv_full_calendar)
        if calendars_list
        else df
    )
    to_write.to_csv(sub / "data.csv", index=False, encoding="utf-8")


def default_worker_count() -> int:
    return max(1, min(32, os.cpu_count() or 8))


def process_all_data(
    data_dir: Path,
    date_str: str,
    st_codes: set[str],
    max_workers: int | None = None,
) -> dict[str, pd.DataFrame]:
    """处理所有股票数据，返回以 qlib_symbol 为 key 的字典"""
    qfq_files = get_qfq_files(data_dir, date_str)
    
    if not qfq_files:
        raise ValueError(f"未找到行情数据: {data_dir / date_str / 'quote' / 'qfq'}")
    
    print(f"找到 {len(qfq_files)} 只股票数据，正在处理...")

    cyq_dir = data_dir / date_str / "quote" / "cyq"
    cyq_file_map = {}
    if cyq_dir.exists():
        for f in cyq_dir.glob("*.csv"):
            ts_code = extract_ts_code_from_filename(f.name)
            if ts_code:
                cyq_file_map[ts_code] = f

    basic_dir = data_dir / date_str / "quote" / "basic"
    basic_file_map: dict[str, Path] = {}
    if basic_dir.exists():
        for f in basic_dir.glob("*.csv"):
            ts_code = extract_ts_code_from_filename(f.name)
            if ts_code:
                basic_file_map[ts_code] = f

    print(f"  - 筹码分布数据: {len(cyq_file_map)} 只")
    print(f"  - daily_basic 基本面: {len(basic_file_map)} 只")
    
    skipped_st = sum(
        1
        for f in qfq_files
        if (c := extract_ts_code_from_filename(f.name)) is not None and c in st_codes
    )

    workers = default_worker_count() if max_workers is None else max(1, max_workers)
    frozen_st = frozenset(st_codes)
    stock_data: dict[str, pd.DataFrame] = {}

    tasks: list[tuple[str, str | None, str | None, frozenset[str]]] = []
    for qfq_file in qfq_files:
        ts_code = extract_ts_code_from_filename(qfq_file.name)
        if not ts_code or ts_code in st_codes:
            continue
        cyq_f = cyq_file_map.get(ts_code)
        basic_f = basic_file_map.get(ts_code)
        tasks.append(
            (
                str(qfq_file.resolve()),
                str(cyq_f.resolve()) if cyq_f else None,
                str(basic_f.resolve()) if basic_f else None,
                frozen_st,
            )
        )

    if workers <= 1:
        for t in tqdm(tasks, desc="处理股票"):
            r = _process_one_stock_worker(*t)
            if r:
                sym, df = r
                stock_data[sym] = df
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(_process_one_stock_worker, *t) for t in tasks]
            for fut in tqdm(as_completed(futures), total=len(futures), desc="处理股票"):
                r = fut.result()
                if r:
                    sym, df = r
                    stock_data[sym] = df

    if skipped_st > 0:
        print(f"已排除 {skipped_st} 只 ST 股票")
    
    if not stock_data:
        raise ValueError("没有有效的数据")
    
    return stock_data


def load_all_index_data(
    data_dir: Path, date_str: str, max_workers: int | None = None
) -> dict[str, pd.DataFrame]:
    """加载所有指数行情数据"""
    index_files = get_index_daily_files(data_dir, date_str)
    if not index_files:
        return {}

    workers = default_worker_count() if max_workers is None else max(1, max_workers)
    index_data: dict[str, pd.DataFrame] = {}
    paths = [str(p.resolve()) for p in index_files]

    if workers <= 1 or len(paths) <= 1:
        for p in tqdm(paths, desc="加载指数数据"):
            r = _process_one_index_worker(p)
            if r:
                sym, df = r
                index_data[sym] = df
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(paths))) as ex:
            futures = [ex.submit(_process_one_index_worker, p) for p in paths]
            for fut in tqdm(as_completed(futures), total=len(futures), desc="加载指数数据"):
                r = fut.result()
                if r:
                    sym, df = r
                    index_data[sym] = df

    return index_data


def save_csv_raw(
    stock_data: dict[str, pd.DataFrame],
    index_data: dict[str, pd.DataFrame],
    output_dir: Path,
    max_workers: int | None = None,
    calendars_list: list[str] | None = None,
    *,
    csv_full_calendar: bool = True,
) -> None:
    """保存 csv_raw。默认全日历对齐（与 ``day.txt`` 起止一致）；``csv_full_calendar=False`` 时仅标的首末日窗口。"""
    csv_dir = output_dir / "csv_raw"
    csv_dir.mkdir(parents=True, exist_ok=True)

    workers = default_worker_count() if max_workers is None else max(1, max_workers)
    stock_items = list(stock_data.items())
    index_items = list(index_data.items())
    all_jobs: list[tuple[str, pd.DataFrame]] = stock_items + index_items

    if workers <= 1 or not all_jobs:
        for qlib_symbol, df in tqdm(all_jobs, desc="保存 CSV"):
            _save_one_csv(qlib_symbol, df, csv_dir, calendars_list, csv_full_calendar)
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(all_jobs))) as ex:
            futures = [
                ex.submit(
                    _save_one_csv,
                    sym,
                    df,
                    csv_dir,
                    calendars_list,
                    csv_full_calendar,
                )
                for sym, df in all_jobs
            ]
            for fut in tqdm(as_completed(futures), total=len(futures), desc="保存 CSV"):
                fut.result()

    print(f"已保存 {len(stock_data)} 只股票和 {len(index_data)} 个指数的 CSV 文件到: {csv_dir}")


def _data_merge_calendar(
    df: pd.DataFrame,
    date_field: str,
    calendar_timestamps: list[pd.Timestamp],
) -> pd.DataFrame:
    """与 Qlib 官方 ``dump_bin.DumpDataBase.data_merge_calendar`` 一致：仅在标的日期范围内截取日历后 reindex。"""
    if df.empty or date_field not in df.columns:
        return pd.DataFrame()
    dmin = df[date_field].min()
    dmax = df[date_field].max()
    cal_index = pd.DatetimeIndex([t for t in calendar_timestamps if dmin <= t <= dmax])
    if len(cal_index) == 0:
        return pd.DataFrame()
    return df.set_index(date_field).reindex(cal_index)


def _align_df_to_calendar(
    df: pd.DataFrame,
    calendars_list: list[str] | None,
    date_field: str = "date",
    *,
    full_calendar: bool = True,
) -> pd.DataFrame:
    """按交易日历补全 CSV 行序。

    - full_calendar=True（默认）：从 calendars_list首日至末日，每交易日一行，与 day.txt 等长；
      标的尚无行情日为 NaN（如上市前）。
    - full_calendar=False：仅在 [标的首条数据日, 末条数据日] 窗口内补行（与转 bin 的 _data_merge_calendar 一致）。
    """
    if not calendars_list or df.empty or date_field not in df.columns:
        return df
    calendar_ts = [pd.Timestamp(d) for d in calendars_list]
    work = df.copy()
    work[date_field] = pd.to_datetime(work[date_field])
    work = work.sort_values(date_field, ascending=True)
    work = work.drop_duplicates(subset=[date_field], keep="first")

    if full_calendar:
        cal_index = pd.DatetimeIndex(calendar_ts)
        merged = work.set_index(date_field).reindex(cal_index)
    else:
        merged = _data_merge_calendar(work, date_field, calendar_ts)

    if merged.empty:
        return df
    out = merged.reset_index()
    if date_field not in out.columns:
        out = out.rename(columns={out.columns[0]: date_field})
    out[date_field] = pd.to_datetime(out[date_field]).dt.strftime("%Y-%m-%d")
    return out


def _prep_dataframe_for_qlib_dump(
    df: pd.DataFrame,
    qlib_symbol: str,
    column_renames: dict[str, str] | None,
) -> pd.DataFrame:
    """构造含 `symbol`、`date` 列的 DataFrame，供 `DumpDataBase._dump_bin` 使用。"""

    prep = df.copy()
    if column_renames:
        ren = {k: v for k, v in column_renames.items() if k in prep.columns and k != v}
        if ren:
            prep = prep.rename(columns=ren)
    prep["symbol"] = qlib_symbol
    prep["date"] = pd.to_datetime(prep["date"])
    return prep


def convert_to_bin(
    stock_data: dict[str, pd.DataFrame],
    index_data: dict[str, pd.DataFrame],
    calendars_list: list[str],
    output_dir: Path,
    writer: DumpDataAll,
    max_workers: int | None = None,
) -> None:
    """将股票和指数数据转换为 Qlib bin（委托 ``dump_bin.DumpDataBase._dump_bin``）。"""

    calendar_ts = [pd.Timestamp(d) for d in calendars_list]
    workers = default_worker_count() if max_workers is None else max(1, max_workers)

    jobs: list[pd.DataFrame] = [
        _prep_dataframe_for_qlib_dump(df, sym, STOCK_BIN_RENAMES) for sym, df in stock_data.items()
    ] + [_prep_dataframe_for_qlib_dump(df, sym, None) for sym, df in index_data.items()]

    if workers <= 1 or not jobs:
        for prep in tqdm(jobs, desc="转换 bin"):
            writer._dump_bin(prep, calendar_ts)
    else:
        with ThreadPoolExecutor(max_workers=min(workers, len(jobs))) as ex:
            futures = [ex.submit(writer._dump_bin, prep, calendar_ts) for prep in jobs]
            for fut in tqdm(as_completed(futures), total=len(futures), desc="转换 bin"):
                fut.result()

    print(f"已转换 {len(stock_data)} 只股票和 {len(index_data)} 个指数的 bin 文件到: {output_dir / 'features'}")


def save_instruments(
    stock_data: dict[str, pd.DataFrame],
    index_data: dict[str, pd.DataFrame],
    index_components: dict[str, set[str]],
    writer: DumpDataAll,
) -> None:
    """保存 instruments：全部走 `dump_bin.DumpDataBase.save_instruments`（与官方一致的 TSV + 符号规范化）。"""

    sym_col = writer.symbol_field_name
    start_f = writer.INSTRUMENTS_START_FIELD
    end_f = writer.INSTRUMENTS_END_FIELD
    instruments_dir = writer._instruments_dir

    stock_ranges: dict[str, tuple[str, str]] = {}
    for qlib_symbol, df in stock_data.items():
        dates = sorted(df["date"].tolist())
        stock_ranges[qlib_symbol] = (dates[0], dates[-1])

    index_ranges: dict[str, tuple[str, str]] = {}
    for qlib_symbol, df in index_data.items():
        dates = sorted(df["date"].tolist())
        index_ranges[qlib_symbol] = (dates[0], dates[-1])

    inst_rows = []
    for qlib_symbol, df in stock_data.items():
        dts = pd.to_datetime(df["date"])
        inst_rows.append(
            {
                sym_col: qlib_symbol,
                start_f: dts.min().strftime("%Y-%m-%d"),
                end_f: dts.max().strftime("%Y-%m-%d"),
            }
        )
    inst_df = pd.DataFrame(inst_rows).sort_values(sym_col)
    writer.save_instruments(inst_df)
    print(f"已保存: {instruments_dir / writer.INSTRUMENTS_FILE_NAME} ({len(stock_ranges)} 只股票)")

    index_rows = [
        {sym_col: symbol, start_f: index_ranges[symbol][0], end_f: index_ranges[symbol][1]}
        for symbol in sorted(index_ranges.keys())
    ]
    writer.save_instruments(pd.DataFrame(index_rows), file_name="index_all.txt")
    print(f"已保存: {instruments_dir / 'index_all.txt'} ({len(index_ranges)} 个指数)")

    for index_name, components in index_components.items():
        comp_rows = []
        for ts_code in sorted(components):
            qlib_symbol = to_qlib_symbol(ts_code)
            if qlib_symbol in stock_ranges:
                start, end = stock_ranges[qlib_symbol]
                comp_rows.append({sym_col: qlib_symbol, start_f: start, end_f: end})
        writer.save_instruments(pd.DataFrame(comp_rows).sort_values(sym_col), file_name=f"{index_name}.txt")
        print(f"已保存: {instruments_dir / f'{index_name}.txt'} ({len(comp_rows)} 只)")


def collect_calendar_dates(
    stock_data: dict[str, pd.DataFrame],
    index_data: dict[str, pd.DataFrame] | None = None,
) -> list[str]:
    """股票与指数（若有）出现过的交易日并集，升序字符串 YYYY-MM-DD。"""

    all_dates: set[str] = set()
    for df in stock_data.values():
        all_dates.update(df["date"].tolist())
    if index_data:
        for df in index_data.values():
            all_dates.update(df["date"].tolist())
    return sorted(all_dates)


def save_calendars_with_writer(
    calendars_as_strings: list[str],
    writer: DumpDataAll,
) -> list[str]:
    """使用 `dump_bin.write_calendars`（与 `DumpDataBase.save_calendars` 相同实现）。"""

    write_calendars(writer.qlib_dir, [pd.Timestamp(d) for d in calendars_as_strings], freq=writer.freq)
    calendar_path = writer._calendars_dir.joinpath(f"{writer.freq}.txt")
    print(f"已保存: {calendar_path} ({len(calendars_as_strings)} 个交易日)")
    return calendars_as_strings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="处理数据并生成 Qlib 格式")
    parser.add_argument("--data-dir", type=str, default="data", help="原始数据目录，默认 data")
    parser.add_argument("--date", type=str, default=None, help="数据日期（如 20260408），默认使用最新日期")
    parser.add_argument("--output-dir", type=str, default="qlib_data", help="输出目录，默认 qlib_data")
    parser.add_argument("--skip-bin", action="store_true", help="跳过 bin 转换，只保存 CSV")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="并行 worker 数（线程池，适用于读 CSV / 写 CSV / 写 bin）；"
        "默认 min(32, CPU 核数)。设为 1 则全程单线程。",
    )
    parser.add_argument(
        "--csv-window-only",
        action="store_true",
        help="csv_raw 仅从标的首条数据日至末日对齐日历（文件更短，首行不是全局起始日）；默认与 day.txt 全日历一致",
    )
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
    workers = args.workers if args.workers is not None else default_worker_count()
    workers = max(1, workers)
    print(f"并行 workers: {workers}")
    print("=" * 60)

    writer = make_process_bin_writer(output_dir, freq="day", max_workers=workers, exclude_fields="symbol")

    # 加载 ST 股票列表
    print("\n正在加载 ST 股票列表...")
    st_codes = load_st_list(data_dir, date_str)
    print(f"ST 股票数量: {len(st_codes)}")
    
    # 加载指数成分股
    print("\n正在加载指数成分股...")
    index_components = load_index_components(data_dir, date_str)
    for name, codes in index_components.items():
        print(f"  - {name}: {len(codes)} 只")
    
    # 处理股票数据
    print("\n正在处理股票数据...")
    stock_data = process_all_data(data_dir, date_str, st_codes, max_workers=workers)
    print(f"有效股票数量: {len(stock_data)}")
    
    # 加载指数数据
    print("\n正在加载指数数据...")
    index_data = load_all_index_data(data_dir, date_str, max_workers=workers)
    print(f"有效指数数量: {len(index_data)}")
    
    # 先写交易日历，再按该日历对齐 csv_raw（否则 CSV 只有 Tushare 有行情的稀疏日）
    print("\n正在保存 calendars...")
    calendars_list = collect_calendar_dates(stock_data, index_data)
    save_calendars_with_writer(calendars_list, writer)

    print("\n正在保存 CSV 原始数据（按 calendars/day.txt 对齐）...")
    save_csv_raw(
        stock_data,
        index_data,
        output_dir,
        max_workers=workers,
        calendars_list=calendars_list,
        csv_full_calendar=not args.csv_window_only,
    )
    
    # 转换为 bin 格式
    if not args.skip_bin:
        print("\n正在转换为 bin 格式...")
        convert_to_bin(
            stock_data,
            index_data,
            calendars_list,
            output_dir,
            writer,
            max_workers=workers,
        )

    # 保存 instruments
    print("\n正在保存 instruments...")
    save_instruments(stock_data, index_data, index_components, writer)
    
    print("\n" + "=" * 60)
    print("数据处理完成")
    print("=" * 60)
    print(f"\n生成的目录结构:")
    print(f"  {output_dir}/")
    print(f"  ├── calendars/day.txt")
    print(f"  ├── instruments/all.txt")
    print(f"  ├── instruments/csi300.txt")
    print(f"  ├── csv_raw/sh600000/data.csv")
    print(f"  └── features/sh600000/*.day.bin")
    print(f"      ...")


if __name__ == "__main__":
    main()
