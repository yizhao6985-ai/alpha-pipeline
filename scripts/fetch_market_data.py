#!/usr/bin/env python3
"""等价 ``make fetch`` / ``python -m scripts.tushare.fetch_market``。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.tushare.fetch_market import main

if __name__ == "__main__":
    main()
