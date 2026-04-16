#!/usr/bin/env python3
"""等价 ``make test`` / ``python -m scripts.verify_qlib.verify_bin``。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.verify_qlib.verify_bin import main

if __name__ == "__main__":
    raise SystemExit(main())
