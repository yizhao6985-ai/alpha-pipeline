"""多块特征按表达式去重合并。"""
from __future__ import annotations


def merge_feature_parts_dedup_expressions(
    parts: list[tuple[list[str], list[str]]],
) -> tuple[list[str], list[str]]:
    """按 ``(field_expr, name)`` 顺序合并；**表达式**已出现则跳过（保留先出现的列名）。"""
    out_f: list[str] = []
    out_n: list[str] = []
    seen: set[str] = set()
    for fields, names in parts:
        for f, n in zip(fields, names):
            if f in seen:
                continue
            seen.add(f)
            out_f.append(f)
            out_n.append(n)
    return out_f, out_n
