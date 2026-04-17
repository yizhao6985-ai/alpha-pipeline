"""解析 ``qlib.init(provider_uri=...)`` 路径。"""
from __future__ import annotations

from scripts.qlib.runtime.constants import PROJECT_ROOT, normalize_writable_path


def resolve_provider_uri(provider_uri: str | None) -> str:
    """``None`` 或空串时使用 ``<仓库根>/qlib_data``；否则为给定目录的绝对路径。"""
    if provider_uri is None or str(provider_uri).strip() == "":
        return str((PROJECT_ROOT / "qlib_data").resolve())
    p = normalize_writable_path(provider_uri)
    if not p.is_dir():
        raise SystemExit(f"Qlib 数据目录不存在或不是目录: {p}")
    return str(p)
