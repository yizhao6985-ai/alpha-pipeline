"""解析 ``qlib.init(provider_uri=...)`` 路径。"""
from __future__ import annotations

from pathlib import Path

# 本文件位于 qlib_lab/，上一级为仓库根
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_provider_uri(provider_uri: str | None) -> str:
    """``None`` 或空串时使用 ``<仓库根>/qlib_data``；否则为给定目录的绝对路径。"""
    if provider_uri is None or str(provider_uri).strip() == "":
        return str((_PROJECT_ROOT / "qlib_data").resolve())
    p = Path(provider_uri).expanduser()
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if not p.is_dir():
        raise SystemExit(f"Qlib 数据目录不存在或不是目录: {p}")
    return str(p)
