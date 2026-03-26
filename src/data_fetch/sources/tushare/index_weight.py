from __future__ import annotations

from .client import build_tushare_clients

INDEX_WEIGHT_FIELD_NAMES = [
    "index_code",
    "con_code",
    "trade_date",
    "weight",
]
INDEX_WEIGHT_FIELDS = ",".join(INDEX_WEIGHT_FIELD_NAMES)


def fetch_index_weight(
    *,
    index_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
):
    _, pro = build_tushare_clients()
    return pro.index_weight(
        index_code=index_code,
        start_date=start_date,
        end_date=end_date,
        fields=INDEX_WEIGHT_FIELDS,
    )
