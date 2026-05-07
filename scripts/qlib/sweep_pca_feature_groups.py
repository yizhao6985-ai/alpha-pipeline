#!/usr/bin/env python3
"""
对 ``lab_fixed_features`` 默认 **55 维** 按 **语义块** 做 PCA 降维实验（每轮只压缩一块，其余列不变）。

**为何这些块值得试 PCA**

- **同族多窗 / 同类几何**：如多条 RSV、多窗 BETA、RESI、量 VMA/VSTD 等，截面相关高，
  PCA 用少数正交方向概括，可能减轻共线性、改变树分裂优先级。
- **MKT_RAW 一整块**：收益、波动、跳空、量比等往往同受市场状态驱动，适合整块压缩。
- **隔夜/跳空子块**：若与标签错频，整块 PCA 有时比单列更稳（也可能更差，需回测）。
- **FUND_RAW 仅 3 列**：PCA 维数低，主要观察「基本面尺度」合成是否优于三列分立。

**注意**：PCA 在 **train** 段 fit，与 RobustZScore 顺序为「先 handler 归一化 → prepare 出矩阵 → 再 PCA」；
与「先 PCA 再 zscore」不同，此处与当前 pipeline 一致。

::

    python -m scripts.qlib sweep_pca_feature_groups --output-parent qlib_runs/pca_sweep
    python -m scripts.qlib sweep_pca_feature_groups --list-groups
    python -m scripts.qlib sweep_pca_feature_groups --groups rsv_family mkt_raw --pca-n-components 2
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from scripts.qlib.backtest.pipeline import run_backtest_pipeline
from scripts.qlib.cli.backtest_args import build_arg_parser, finalize_backtest_cli_args
from scripts.qlib.dataset.from_args import build_training_dataset
from scripts.qlib.dataset.group_pca_wrapper import GroupPCADatasetWrapper
from scripts.qlib.handler.features.lab_fixed_features import lab_fixed_feature_config
from scripts.qlib.runtime import init_qlib_for_backtest
from scripts.qlib.runtime.constants import normalize_writable_path


def _all_feature_names() -> list[str]:
    return list(lab_fixed_feature_config()[1])


def default_pca_groups(names: list[str]) -> dict[str, list[str]]:
    """按列名规则划分块；块内至少 2 列才会被 PCA（脚本内再校验）。"""

    def pick(pred: Callable[[str], bool]) -> list[str]:
        return [n for n in names if pred(n)]

    groups: dict[str, list[str]] = {
        "rsv_family": pick(lambda n: "RSV" in n),
        "mkt_raw_block": pick(lambda n: n.startswith("MKT_RAW")),
        "fund_raw_block": pick(lambda n: n.startswith("FUND_RAW")),
        "beta_slope_block": pick(lambda n: "BETA" in n),
        "resi_block": pick(lambda n: "RESI" in n),
        "roc_std_block": pick(
            lambda n: any(
                x in n
                for x in (
                    "ROC5",
                    "ROC10",
                    "STD20",
                    "STD30",
                    "STD60",
                    "RSQR30",
                )
            )
        ),
        "vma_vstd_block": pick(
            lambda n: "VMA" in n or "VSTD" in n or "VSUMP" in n
        ),
        "kline_shape_block": pick(
            lambda n: any(
                x in n
                for x in (
                    "KUP",
                    "KLOW",
                    "KMID",
                    "KSFT",
                    "KMUP",
                )
            )
        ),
        "tr_vol_mom_block": pick(
            lambda n: any(
                x in n
                for x in (
                    "TR_MEAN",
                    "STDRATIO",
                    "EWMA_SQRET",
                    "HL_RANGE",
                    "MOM20_OVER_VOL",
                    "DLOG_VOL",
                )
            )
        ),
        "gap_overnight_block": pick(
            lambda n: any(x in n for x in ("GAP", "ON_RET_PREV"))
        ),
        "ma_price_block": pick(
            lambda n: n in ("A158_MA5", "A158_MA20", "A158_MA30")
        ),
        "min_max_block": pick(lambda n: "MIN" in n or "MAX" in n),
    }
    return {k: v for k, v in groups.items() if len(v) >= 2}


def _safe_subdir(name: str, *, max_len: int = 80) -> str:
    s = "".join(c if (c.isalnum() or c in "-._") else "_" for c in name.strip())
    return (s.strip("_") or "group")[:max_len]


def parse_args() -> argparse.Namespace:
    p = build_arg_parser()
    g = p.add_argument_group("PCA 块扫参（本模块）")
    g.add_argument(
        "--output-parent",
        type=Path,
        default=Path("qlib_runs") / "pca_feature_groups",
        help="父目录：每块一个子目录 + 汇总 CSV",
    )
    g.add_argument(
        "--groups",
        nargs="*",
        default=[],
        metavar="ID",
        help="只跑这些块 id（默认跑 default_pca_groups 中全部）",
    )
    g.add_argument(
        "--list-groups",
        action="store_true",
        help="打印可用块及列名后退出",
    )
    g.add_argument(
        "--pca-n-components",
        type=int,
        default=None,
        metavar="K",
        help="每块保留主成分数（默认 min(3, 块内列数)）",
    )
    return finalize_backtest_cli_args(p.parse_args())


def main() -> int:
    args = parse_args()
    names = _all_feature_names()
    groups = default_pca_groups(names)

    if getattr(args, "list_groups", False):
        print("PCA 块（至少 2 列）：", file=sys.stderr)
        for gid, cols in sorted(groups.items()):
            print(f"  [{gid}] ({len(cols)}): {', '.join(cols)}", file=sys.stderr)
        return 0

    want = [g.strip() for g in (getattr(args, "groups", None) or []) if g.strip()]
    if want:
        missing = [g for g in want if g not in groups]
        if missing:
            raise SystemExit(f"未知 --groups: {missing!r}。使用 --list-groups 查看。")
        run_map = {g: groups[g] for g in want}
    else:
        run_map = dict(groups)

    if not run_map:
        raise SystemExit("没有可跑的 PCA 块（每块至少需 2 列）。")

    out_parent = normalize_writable_path(args.output_parent)
    out_parent.mkdir(parents=True, exist_ok=True)

    init_qlib_for_backtest(args)
    base_ds = build_training_dataset(args)

    rows: list[dict[str, object]] = []
    k = getattr(args, "pca_n_components", None)

    for gid, cols in sorted(run_map.items()):
        sub = _safe_subdir(gid)
        run_dir = out_parent / sub
        run_dir.mkdir(parents=True, exist_ok=True)
        exp = f"{args.experiment_name}_pca_{sub}".replace(".", "_")
        print(f"--- PCA 块 {gid} ({len(cols)}→k) → {run_dir} ---", file=sys.stderr)

        wrapped = GroupPCADatasetWrapper(
            base_ds,
            cols,
            tag=sub,
            n_components=k,
        )
        _, end_tr = run_backtest_pipeline(
            args,
            dataset=wrapped,
            output_dir=run_dir,
            experiment_name=exp,
        )
        try:
            rel = run_dir.relative_to(out_parent)
        except ValueError:
            rel = run_dir
        rows.append(
            {
                "pca_group_id": gid,
                "n_cols_in_block": len(cols),
                "pca_n_components": len(wrapped._out_names),
                "experiment_name": exp,
                "artifact_subdir": str(rel),
                "portfolio_total_return": end_tr,
            }
        )
        print(f"  portfolio_total_return={end_tr}", file=sys.stderr)

    summary = out_parent / "pca_group_sweep_summary.csv"
    pd.DataFrame(rows).to_csv(summary, index=False)
    print(f"已写入汇总: {summary}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
