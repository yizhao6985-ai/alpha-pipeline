"""仓库与运行环境路径。"""
from __future__ import annotations

from pathlib import Path

# qlib_lab 包目录的上一级 = 仓库根
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
