#!/usr/bin/env python3
"""薄转发：``python scripts/sweep_pca_feature_groups.py`` → ``scripts.qlib.sweep_pca_feature_groups``。"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.qlib.sweep_pca_feature_groups import main

if __name__ == "__main__":
    raise SystemExit(main())
