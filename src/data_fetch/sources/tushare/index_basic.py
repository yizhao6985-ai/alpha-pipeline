from __future__ import annotations

from typing import cast

import pandas as pd

from ...runtime import (
    get_default_index_basic_markets,
    get_default_stock_index_basic_categories,
)
from .client import build_tushare_clients

INDEX_BASIC_FIELD_NAMES = [
    "ts_code",
    "name",
    "fullname",
    "market",
    "publisher",
    "index_type",
    "category",
    "base_date",
    "base_point",
    "list_date",
    "weight_rule",
    "desc",
    "exp_date",
]
INDEX_BASIC_FIELDS = ",".join(INDEX_BASIC_FIELD_NAMES)


def _fetch_index_basic(market: str):
    _, pro = build_tushare_clients()
    return pro.index_basic(market=market, fields=INDEX_BASIC_FIELDS)


def fetch_index_basic():
    frames = [_fetch_index_basic(market=market) for market in get_default_index_basic_markets()]
    return pd.concat(frames, ignore_index=True)


def filter_stock_index_basic(index_basic_df: pd.DataFrame) -> pd.DataFrame:
    if index_basic_df.empty:
        return index_basic_df

    category_mask = index_basic_df["category"].fillna("").isin(get_default_stock_index_basic_categories())
    filtered_df = index_basic_df.loc[category_mask].reset_index(drop=True)
    return cast(pd.DataFrame, filtered_df)
