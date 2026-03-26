from __future__ import annotations

from ...config import get_required_env


def build_tushare_clients():
    import tushare as ts

    token = get_required_env("TUSHARE_TOKEN")
    ts.set_token(token)
    return ts, ts.pro_api(token)
