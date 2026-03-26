from __future__ import annotations

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FETCH_START_DATE = "20180101"


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"缺少环境变量 {name}，请参考 .env.example 配置")
    return value


def get_default_fetch_start_date() -> str:
    return DEFAULT_FETCH_START_DATE


def get_default_fetch_end_date() -> str:
    return datetime.today().strftime("%Y%m%d")


