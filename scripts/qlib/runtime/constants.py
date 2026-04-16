"""仓库与运行环境路径。"""
from __future__ import annotations

from pathlib import Path

# scripts/qlib/runtime/constants.py → 仓库根
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
