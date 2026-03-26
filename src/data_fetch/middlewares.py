from __future__ import annotations

from .fetcher import Middleware, MiddlewareKey
from .source_middlewares import build_tushare_middlewares


def build_default_middlewares() -> dict[MiddlewareKey, list[Middleware]]:
    return build_tushare_middlewares()
