"""基于 ``feature_importance.csv`` 的特征长尾集中度（辅助判断噪声占比）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def summarize_feature_importance_tail(
    importance_path: Path,
    *,
    tail_pct: float = 20.0,
) -> dict[str, Any] | None:
    """读取 gain 列，计算 Top 占比、尾部累计占比、归一化赫芬达尔指数等。"""
    path = Path(importance_path)
    if not path.exists():
        return None
    df = pd.read_csv(path)
    col = "importance_gain" if "importance_gain" in df.columns else None
    if col is None:
        for c in df.columns:
            if "importance" in c.lower() or "gain" in c.lower():
                col = c
                break
    if col is None or df.empty:
        return None
    g = pd.to_numeric(df[col], errors="coerce").fillna(0.0).values.astype(float)
    g = np.maximum(g, 0.0)
    s = g.sum()
    if s <= 0:
        return {"n_features": len(g), "error": "zero_total_gain"}
    p = g / s
    order = np.argsort(-g)
    sorted_p = p[order]
    cum = np.cumsum(sorted_p)
    n = len(g)
    k_tail = max(1, int(np.ceil(n * float(tail_pct) / 100.0)))
    tail_mass = float(sorted_p[-k_tail:].sum())
    top10 = max(1, int(np.ceil(n * 0.10)))
    top10_mass = float(sorted_p[:top10].sum())
    hhi = float((p**2).sum())
    return {
        "n_features": n,
        "tail_pct_definition": float(tail_pct),
        "tail_n_features": k_tail,
        "tail_cumulative_gain_share": tail_mass,
        "top10pct_n_features": top10,
        "top10pct_cumulative_gain_share": top10_mass,
        "normalized_hhi": hhi,
    }


def write_feature_tail_diag_csv(
    importance_path: Path,
    out_path: Path,
    *,
    tail_pct: float = 20.0,
) -> Path | None:
    summary = summarize_feature_importance_tail(importance_path, tail_pct=tail_pct)
    if summary is None:
        return None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([summary]).to_csv(out_path, index=False)
    return out_path
