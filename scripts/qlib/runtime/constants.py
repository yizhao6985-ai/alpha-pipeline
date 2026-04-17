"""仓库与运行环境路径。"""
from __future__ import annotations

import sys
from pathlib import Path

# scripts/qlib/runtime/constants.py → 仓库根
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]


def normalize_writable_path(path: Path | str) -> Path:
    """解析用于写文件的目录/文件路径为绝对路径。

    macOS 上常见误将本机绝对路径写成 ``Users/name/...``（缺少前导 ``/``），
    ``Path`` 会按相对路径落在当前工作目录下，误建 ``Users`` 目录。此处对
    **非绝对路径且首段为 ``Users``** 的情况补成 ``/Users/...``。
    """
    p = Path(path).expanduser()
    if p.is_absolute():
        return p.resolve()
    if sys.platform == "darwin" and p.parts and p.parts[0] == "Users":
        return (Path("/") / p).resolve()
    return p.resolve()
