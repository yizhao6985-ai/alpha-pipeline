"""
基础工具函数
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()


def get_required_env(name: str) -> str:
    """获取必需的环境变量"""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"缺少环境变量 {name}，请参考 .env.example 配置")
    return value


def get_tushare_pro():
    """获取 Tushare pro_api 实例"""
    import tushare as ts

    token = get_required_env("TUSHARE_TOKEN")
    ts.set_token(token)
    return ts.pro_api(token)


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save_csv(df: pd.DataFrame, path: Path) -> None:
    """保存 DataFrame 为 CSV 文件"""
    ensure_dir(path)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存: {path}")


def file_exists_and_not_empty(path: Path) -> bool:
    """检查文件是否存在且非空"""
    return path.exists() and path.stat().st_size > 0
