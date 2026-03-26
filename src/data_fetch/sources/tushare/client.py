from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from ...config import get_required_env

T = TypeVar("T")

_TRANSIENT_ERROR_NAME_KEYWORDS = (
    "ConnectionError",
    "ProtocolError",
    "Timeout",
    "ChunkedEncodingError",
    "RemoteDisconnected",
)
_TRANSIENT_ERROR_MESSAGE_KEYWORDS = (
    "connection reset",
    "connection aborted",
    "timed out",
    "temporarily unavailable",
    "remote end closed connection",
)


def build_tushare_clients():
    import tushare as ts

    token = get_required_env("TUSHARE_TOKEN")
    ts.set_token(token)
    return ts, ts.pro_api(token)


def is_transient_network_error(exc: Exception) -> bool:
    name = type(exc).__name__
    name_matched = any(keyword in name for keyword in _TRANSIENT_ERROR_NAME_KEYWORDS)
    if name_matched:
        return True
    message = str(exc).lower()
    return any(keyword in message for keyword in _TRANSIENT_ERROR_MESSAGE_KEYWORDS)


def call_with_retry(
    func: Callable[[], T],
    *,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> T:
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as exc:
            if not is_transient_network_error(exc) or attempt >= retries:
                raise
            time.sleep(backoff_seconds * attempt)

    # Unreachable, only for static type completeness.
    raise RuntimeError("call_with_retry: unexpected control flow")
