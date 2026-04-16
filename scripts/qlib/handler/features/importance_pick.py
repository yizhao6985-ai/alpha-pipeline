"""按 LightGBM gain CSV 在合并特征集中截取子集。"""
from __future__ import annotations

import csv
import os
from pathlib import Path


def resolve_importance_csv_path(explicit: Path | str | None) -> Path:
    """显式路径优先，否则 ``QLIB_LAB_FEATURE_IMPORTANCE_CSV``，否则本目录下 ``feature_importance_baseline.csv``。"""
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("QLIB_LAB_FEATURE_IMPORTANCE_CSV", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve().parent
    return (here / "feature_importance_baseline.csv").resolve()


def load_importance_gain_csv(path: Path) -> dict[str, float]:
    """读取 ``feature_importance.csv`` 风格表（列 ``feature``, ``importance_gain``）。"""
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or "feature" not in reader.fieldnames or "importance_gain" not in reader.fieldnames:
            raise ValueError(f"importance CSV 须含 feature、importance_gain 列: {path}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"importance CSV 无数据行: {path}")
    out: dict[str, float] = {}
    for row in rows:
        k = str(row["feature"]).strip()
        try:
            out[k] = float(row["importance_gain"])
        except (TypeError, ValueError):
            out[k] = 0.0
    return out


def order_indices_by_gain(names: list[str], gain: dict[str, float]) -> list[int]:
    """按 gain 降序排特征下标。键可为 handler 列名，或 LightGBM 的 ``Column_{i}``（与矩阵列序一致）。"""
    scored: list[tuple[float, int]] = []
    for i, n in enumerate(names):
        g = gain.get(str(n))
        if g is None:
            g = gain.get(f"Column_{i}", 0.0)
        scored.append((float(g), i))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in scored]


def pick_topk_fields_by_importance(
    fields: list[str],
    names: list[str],
    *,
    importance_csv: Path | str | None,
    top_k: int,
) -> tuple[list[str], list[str]]:
    """在 ``fields/names`` 上按 CSV gain 降序取前 ``top_k`` 列（输出顺序同 importance 序）。"""
    if top_k < 0:
        raise ValueError("top_k 须为非负整数")
    path = resolve_importance_csv_path(importance_csv)
    if not path.is_file():
        raise FileNotFoundError(
            f"按 importance 取前 {top_k} 列需要 CSV（列 feature, importance_gain），未找到: {path}\n"
            "请设置环境变量 QLIB_LAB_FEATURE_IMPORTANCE_CSV，或将文件放到上述路径，"
            "或在 full_feature_config_unpruned(importance_csv=...) 传入路径。\n"
            "默认无需 CSV：请使用 max_features=None 或 CLI --feature-top-k 0 做全量训练并导出 feature_importance.csv，再设 K>0。"
        )
    gain = load_importance_gain_csv(path)
    ranked = order_indices_by_gain(names, gain)
    pick = ranked[: min(top_k, len(ranked))]
    return [fields[i] for i in pick], [names[i] for i in pick]
