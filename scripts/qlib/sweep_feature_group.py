#!/usr/bin/env python3
"""
在 **本文件** 配置若干 ``(Qlib 表达式, 列名)`` 候选；执行时基准特征仍来自
``lab_fixed_features``（由 ``--feature-preset`` 等决定），**每一轮只把其中一条候选**
与基准合并后训练 + 回测。默认先跑一轮仅基准，便于对照。

::

    python -m scripts.qlib sweep_feature_group --output-parent qlib_runs/my_ablation

``--feature-names`` / ``--feature-names-file`` 可选：按 **列名** 从下方
``SWEEP_FEATURE_GROUP_CANDIDATES`` 里筛选子集（不填则跑全部候选）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from scripts.qlib.backtest.pipeline import run_backtest_pipeline
from scripts.qlib.cli.backtest_args import build_arg_parser, finalize_backtest_cli_args
from scripts.qlib.dataset.from_args import (
    _build_training_dataset_with_fields,
    _feature_config_from_args,
)
from scripts.qlib.runtime import init_qlib_for_backtest
from scripts.qlib.runtime.constants import normalize_writable_path

# ---------------------------------------------------------------------------
# 候选特征：(field_expr, column_name)，与 lab_fixed_features 中元组格式相同。
# 每轮取其中一条与基准合并；列名勿与基准集中已有列重复（重复则跳过）。
#
# **与 55 维的关系（为何换一批）**
# lab 里 RSV 多窗、MA5/20/30、量/额对数及波动、K 线几何、BETA10/20/60、MOM20_OVER_VOL、
# STDRATIO 5/60、Corr(close,log vol,30) 等已覆盖「区间位置 / 均线比 / 量噪 / 价量 30 日相关」。
# 上一批 sweep 多为同类变换（再补 RSV 窗、CLV、量 Z、额比），与树已有分裂高度共线，易稀释增益。
#
# **本组方向（与现有表错开）**
# - FUND 仅 3 列：补「流通相对总市值」结构，而非再堆 OHLC 变形。
# - 趋势窗：10↔20↔60 之间有 **15 日斜率**；另做 **短长斜率差** 显式交互。
# - 线性度：仅 RSQR30 → 补 **10 与 30 的 R² 差**（趋势从稳变乱）。
# - 微观结构：**Amihud 类**（|日收益|/log 额），与 HL_RANGE、log 额单列不同。
# - 经典双均线：**12/26 价格比**，与单条 MA/close 比不同。
# - 量：**变异系数** Std/Mean，与 VSTD/VMA 比值信息角度不同。
# - 隔夜×日内：**跳空强度 × 日内涨跌**（若标签与隔夜相关，可能单独有用）。
# - 价量相关：**15 日** 居中于已有 30 日。
# ---------------------------------------------------------------------------
SWEEP_FEATURE_GROUP_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("Log($circ_mv + 1) - Log($total_mv + 1)", "SWEEP_LOG_FLOAT_OVER_TOTAL"),
    ("Slope($close, 15) / $close", "SWEEP_BETA15"),
    ("Rsquare($close, 10) - Rsquare($close, 30)", "SWEEP_RSQR10_MINUS_RSQR30"),
    (
        "Abs($close / Ref($close, 1) - 1) / (Log($money + 1) + 1e-12)",
        "SWEEP_AMIHUD_RET_OVER_LOGMONEY",
    ),
    ("Mean($close, 12) / Mean($close, 26) - 1", "SWEEP_MA12_OVER_MA26"),
    ("Std($volume, 5) / (Mean($volume, 20) + 1e-12)", "SWEEP_VOL_CV5_OVER_M20"),
    (
        "(($open - Ref($close, 1)) / (Ref($close, 1) + 1e-12)) * (($close - $open) / ($open + 1e-12))",
        "SWEEP_GAP_TODAY_X_INTRADAY_RET",
    ),
    (
        "Slope($close, 10) / $close - Slope($close, 60) / $close",
        "SWEEP_BETA10_MINUS_BETA60",
    ),
    ("Corr($close, Log($volume + 1), 15)", "SWEEP_CORR_CLOSE_LOGVOL15"),
)


def _read_sigana_mean_from_out_dir(out_dir: Path, name: str) -> float | None:
    """从 ``record_viz/sig_analysis/{ic|rank_ic}_stats.csv`` 读取单列 ``mean``。"""
    p = Path(out_dir) / "record_viz" / "sig_analysis" / f"{name}_stats.csv"
    if not p.exists():
        return None
    try:
        df = pd.read_csv(p)
    except Exception:  # noqa: BLE001
        return None
    if df.empty or "mean" not in df.columns:
        return None
    return float(df["mean"].iloc[0])


def _safe_subdir(name: str, *, max_len: int = 120) -> str:
    s = "".join(c if (c.isalnum() or c in "-._") else "_" for c in name.strip())
    s = s.strip("_") or "feature"
    return s[:max_len]


def _run_one_round(
    args: argparse.Namespace,
    out_parent: Path,
    fields: list[str],
    names: list[str],
    *,
    artifact_subdir: str,
    experiment_name: str,
    added_feature_name: str,
    added_feature_expr: str,
    n_base_features: int,
) -> dict[str, object]:
    sub = _safe_subdir(artifact_subdir)
    run_dir = out_parent / sub
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"--- {experiment_name} → {run_dir} ---", file=sys.stderr)

    ds = _build_training_dataset_with_fields(args, fields, names)
    _, end_tr = run_backtest_pipeline(
        args,
        dataset=ds,
        output_dir=run_dir,
        experiment_name=experiment_name,
    )

    try:
        rel = run_dir.relative_to(out_parent)
    except ValueError:
        rel = run_dir

    row: dict[str, object] = {
        "added_feature_name": added_feature_name,
        "added_feature_expr": added_feature_expr,
        "n_base_features": n_base_features,
        "n_features_total": len(names),
        "experiment_name": experiment_name,
        "artifact_subdir": str(rel),
        "portfolio_total_return": end_tr,
        "sigana_ic_mean": _read_sigana_mean_from_out_dir(run_dir, "ic"),
        "sigana_rank_ic_mean": _read_sigana_mean_from_out_dir(run_dir, "rank_ic"),
    }
    print(f"  portfolio_total_return={end_tr}", file=sys.stderr)
    return row


def _module_candidate_map() -> dict[str, str]:
    """列名 -> 表达式；``SWEEP_FEATURE_GROUP_CANDIDATES`` 内列名须唯一。"""
    out: dict[str, str] = {}
    for expr, col in SWEEP_FEATURE_GROUP_CANDIDATES:
        c = col.strip()
        if not c:
            raise SystemExit("SWEEP_FEATURE_GROUP_CANDIDATES 中存在空列名")
        if c in out:
            raise SystemExit(
                f"SWEEP_FEATURE_GROUP_CANDIDATES 中列名重复: {c!r}（请保证列名唯一）"
            )
        out[c] = expr
    return out


def _collect_filter_names(args: argparse.Namespace) -> list[str]:
    """``--feature-names`` / ``--feature-names-file``：按列名筛选候选，可空表示不筛选。"""
    names: list[str] = []
    path = getattr(args, "feature_names_file", None)
    if path is not None:
        p = Path(path)
        if not p.is_file():
            raise SystemExit(f"--feature-names-file 不是文件: {p}")
        for line in p.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                names.append(s)
    extra = getattr(args, "feature_names", None) or []
    names.extend(str(x).strip() for x in extra if str(x).strip())
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _resolve_sweep_candidates(
    args: argparse.Namespace,
) -> tuple[list[tuple[str, str]], str]:
    """返回 ``[(expr, col), ...]`` 及来源说明。"""
    cmap = _module_candidate_map()
    filters = _collect_filter_names(args)
    if filters:
        missing = [n for n in filters if n not in cmap]
        if missing:
            known = ", ".join(sorted(cmap)[:12])
            more = "…" if len(cmap) > 12 else ""
            raise SystemExit(
                f"下列列名未在 SWEEP_FEATURE_GROUP_CANDIDATES 中配置: {missing!r}\n"
                f"已配置的列名示例: {known}{more}"
            )
        pairs = [(cmap[n], n) for n in filters]
        return pairs, "cli_filter"
    if not cmap:
        raise SystemExit(
            "SWEEP_FEATURE_GROUP_CANDIDATES 为空：请在本文件至少配置一条 (表达式, 列名)。"
        )
    pairs = [(cmap[c], c) for c in cmap]
    return pairs, "module"


def parse_args() -> argparse.Namespace:
    p = build_arg_parser()
    g = p.add_argument_group("基准 + 单候选列轮询（本模块）")
    g.add_argument(
        "--feature-names",
        nargs="*",
        default=[],
        metavar="NAME",
        help="列名，可多次出现；与 --feature-names-file 合并后，用于从 SWEEP_FEATURE_GROUP_CANDIDATES 筛选子集",
    )
    g.add_argument(
        "--feature-names-file",
        type=Path,
        default=None,
        help="每行一个列名（须为本文件 SWEEP_FEATURE_GROUP_CANDIDATES 中已配置的列名），# 开头为注释",
    )
    g.add_argument(
        "--output-parent",
        type=Path,
        default=Path("qlib_runs") / "feature_one_of_group",
        help="父目录：其下为每个「追加的候选列」一个子目录（默认 qlib_runs/feature_one_of_group）",
    )
    g.add_argument(
        "--no-baseline",
        action="store_true",
        help="不跑仅基准特征的一轮（默认会跑，输出子目录 baseline/）",
    )
    return finalize_backtest_cli_args(p.parse_args())


def main() -> int:
    args = parse_args()
    candidates, feat_source = _resolve_sweep_candidates(args)

    out_parent = normalize_writable_path(args.output_parent)
    out_parent.mkdir(parents=True, exist_ok=True)

    init_qlib_for_backtest(args)

    base_fields, base_names = _feature_config_from_args(args)
    preset = getattr(args, "feature_preset", "full")
    n_base = len(base_names)
    src_note = "CLI 筛选" if feat_source == "cli_filter" else "SWEEP_FEATURE_GROUP_CANDIDATES 全部"
    print(
        f"基准特征: {n_base} 列 (preset={preset})；本轮追加候选 {len(candidates)} 条（{src_note}）；"
        f"{'先跑基准，再' if not getattr(args, 'no_baseline', False) else ''}"
        f"每条追加 1 列",
        file=sys.stderr,
    )

    rows: list[dict[str, object]] = []

    if not getattr(args, "no_baseline", False):
        exp_base = f"{args.experiment_name}_baseline".replace(".", "_")
        rows.append(
            _run_one_round(
                args,
                out_parent,
                list(base_fields),
                list(base_names),
                artifact_subdir="baseline",
                experiment_name=exp_base,
                added_feature_name="(baseline)",
                added_feature_expr="",
                n_base_features=n_base,
            )
        )

    for expr, col in candidates:
        if col in base_names:
            print(
                f"--- 跳过（该列名已在基准集中，与 lab_fixed 重复）: {col} ---",
                file=sys.stderr,
            )
            continue

        fields = list(base_fields) + [expr]
        names = list(base_names) + [col]
        sub = _safe_subdir(col)
        exp = f"{args.experiment_name}_addfeat_{sub}".replace(".", "_")
        rows.append(
            _run_one_round(
                args,
                out_parent,
                fields,
                names,
                artifact_subdir=col,
                experiment_name=exp,
                added_feature_name=col,
                added_feature_expr=expr,
                n_base_features=n_base,
            )
        )

    if not rows:
        raise SystemExit(
            "没有产生任何有效运行：已加 --no-baseline 且候选全部跳过，或候选为空。"
        )

    summary = out_parent / "feature_group_sweep_summary.csv"
    pd.DataFrame(rows).to_csv(summary, index=False)
    print(f"已写入汇总: {summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
