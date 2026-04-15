#!/usr/bin/env python3
"""
按 LightGBM gain（或外部 CSV）排序特征，从尾部按 **累计剔除比例** 做网格，每次全量重训 + ``backtest_daily`` 并汇总指标。

剔除比例 ``tail_remove_pct`` 含义：从基准 ``N`` 列中去掉 gain 最低的 ``floor(N * pct / 100)`` 列，至少保留 1 列。
默认基准与常规训练一致，为 ``full_feature_config_pruned_top508()``（508 列）；可用 ``--tail-baseline unpruned`` 改为全量 604 列。

与 ``run_qlib_backtest`` 共用数据与训练相关参数；额外参数::

    python -m qlib_lab.sweep_tail_feature_backtest \\
        --tail-min-pct 0 --tail-max-pct 30 --tail-step-pct 5 \\
        --output-dir ./qlib_runs/tail_sweep

可选 ``--importance-csv``：列 ``feature``, ``importance_gain``（与 ``feature_importance.csv`` 一致）。
须与当前 ``--tail-baseline`` 下列数一致（例如 pruned 下应为 508 列模型导出的 CSV），否则排序会不准。
不提供时先在基准特征集上训练一次，用当次 gain 作为排序依据（该次结果也会写入网格的第一行，若 min=0）。

输出：``<output-dir>/tail_feature_sweep.csv``；各档 ``feature_importance.csv`` 等在 ``<output-dir>/tail_<pct>/``。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from qlib.workflow import R

from qlib_lab.backtest import (
    backtest_daily_with_trained,
    build_backtest_config_from_args,
    end_total_return_from_report_normal,
)
from qlib_lab.cli.backtest import build_arg_parser
from qlib_lab.dataset import build_training_dataset
from qlib_lab.handler import full_feature_config_pruned_top508, full_feature_config_unpruned
from qlib_lab.runtime import init_qlib_for_backtest
from qlib_lab.strategy import build_strategy_config_from_args
from qlib_lab.training import fit_model_generate_pred


def _load_importance_csv(path: Path) -> dict[str, float]:
    df = pd.read_csv(path)
    if "feature" not in df.columns or "importance_gain" not in df.columns:
        raise SystemExit(f"importance CSV 需含 feature、importance_gain 列: {path}")
    out: dict[str, float] = {}
    for _, row in df.iterrows():
        k = str(row["feature"]).strip()
        try:
            out[k] = float(row["importance_gain"])
        except (TypeError, ValueError):
            out[k] = 0.0
    return out


def _order_indices_by_gain(names: list[str], gain: dict[str, float]) -> list[int]:
    """按 gain 降序排特征下标。gain 键可为 handler 列名，或 LightGBM 的 ``Column_{i}``（与矩阵列序一致）。"""
    scored: list[tuple[float, int]] = []
    for i, n in enumerate(names):
        g = gain.get(str(n))
        if g is None:
            g = gain.get(f"Column_{i}", 0.0)
        scored.append((float(g), i))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [i for _, i in scored]


def _subset_by_tail_pct(
    fields: list[str],
    names: list[str],
    order_idx: list[int],
    tail_remove_pct: float,
) -> tuple[list[str], list[str]]:
    n_total = len(names)
    if n_total == 0:
        return [], []
    n_drop = int(n_total * float(tail_remove_pct) / 100.0)
    n_drop = min(max(0, n_drop), n_total - 1)
    n_keep = n_total - n_drop
    keep_idx = order_idx[:n_keep]
    return [fields[i] for i in keep_idx], [names[i] for i in keep_idx]


def _tail_pct_grid(pmin: float, pmax: float, step: float) -> list[float]:
    if step <= 0:
        raise SystemExit("--tail-step-pct 须为正数")
    if pmax < pmin:
        raise SystemExit("--tail-max-pct 须 >= --tail-min-pct")
    out: list[float] = []
    x = float(pmin)
    while x <= pmax + 1e-9:
        out.append(round(x, 6))
        x += step
    return out


def parse_sweep_args() -> argparse.Namespace:
    p = build_arg_parser()
    g = p.add_argument_group("尾部特征剔除网格（本模块）")
    g.add_argument(
        "--tail-baseline",
        choices=("pruned", "unpruned"),
        default="pruned",
        help="网格基准特征集：pruned=与默认训练相同的 gain 前 508 列；unpruned=全量合并列（约 604）",
    )
    g.add_argument(
        "--tail-min-pct",
        type=float,
        default=0.0,
        help="累计剔除比例下限（%%），0 表示不剔除（保留基准集全部列）",
    )
    g.add_argument(
        "--tail-max-pct",
        type=float,
        default=30.0,
        help="累计剔除比例上限（%%）",
    )
    g.add_argument(
        "--tail-step-pct",
        type=float,
        default=5.0,
        help="网格步长（%%），例如 5 表示 0%%、5%%、10%%…",
    )
    g.add_argument(
        "--importance-csv",
        type=Path,
        default=None,
        metavar="PATH",
        help="可选；列 feature, importance_gain。省略时先跑全量训练得到 gain 再扫网格",
    )
    g.add_argument(
        "--sweep-subdir-prefix",
        type=str,
        default="tail",
        help="各档输出子目录名前缀：{prefix}_{pct}/",
    )
    return p.parse_args()


def main() -> int:
    args = parse_sweep_args()
    out_root = args.output_dir.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    grid = _tail_pct_grid(args.tail_min_pct, args.tail_max_pct, args.tail_step_pct)

    init_qlib_for_backtest(args)

    if args.tail_baseline == "pruned":
        full_fields, full_names = full_feature_config_pruned_top508()
    else:
        full_fields, full_names = full_feature_config_unpruned()
    n_full = len(full_names)
    if n_full == 0:
        raise SystemExit("全量特征为空")

    gain_map: dict[str, float] | None = None
    order_idx: list[int] | None = None
    if args.importance_csv is not None:
        gain_map = _load_importance_csv(args.importance_csv.expanduser().resolve())
        order_idx = _order_indices_by_gain(full_names, gain_map)
        print(f"已从 CSV 加载 {len(gain_map)} 条 importance 记录", file=sys.stderr)
    elif args.tail_min_pct > 0:
        raise SystemExit("未提供 --importance-csv 时请令 --tail-min-pct=0（首档全量训练以得到 gain）")

    rows: list[dict] = []

    for pct in grid:
        if order_idx is None:
            if pct != 0:
                raise SystemExit("无 --importance-csv 时网格须从 0%% 开始（当前首档不为 0）")
            sub_f, sub_n = full_fields, full_names
        else:
            sub_f, sub_n = _subset_by_tail_pct(full_fields, full_names, order_idx, pct)
        n_feat = len(sub_n)
        n_drop = n_full - n_feat
        print(f"--- tail_remove_pct={pct}% 保留 {n_feat}/{n_full} 列（剔除 {n_drop}）---", file=sys.stderr)

        dataset = build_training_dataset(
            args,
            feature_config=(sub_f, sub_n),
        )
        port_config = {
            "strategy": build_strategy_config_from_args(args),
            "backtest": build_backtest_config_from_args(args),
        }
        exp = f"{args.experiment_name}_{args.sweep_subdir_prefix}_{pct:g}".replace(".", "_")
        sub_out = out_root / f"{args.sweep_subdir_prefix}_{pct:g}".replace(".", "_")
        sub_out.mkdir(parents=True, exist_ok=True)

        with R.start(experiment_name=exp):
            model = fit_model_generate_pred(args, dataset)
            report_normal, _ = backtest_daily_with_trained(model, dataset, port_config)
            end_tr = end_total_return_from_report_normal(report_normal)
            if model.model is not None:
                fi_series = model.get_feature_importance(importance_type="gain")
                pd.DataFrame(
                    {"feature": fi_series.index.astype(str), "importance_gain": fi_series.values}
                ).to_csv(sub_out / "feature_importance.csv", index=False)

            if gain_map is None and model.model is not None:
                fi0 = model.get_feature_importance(importance_type="gain")
                gain_map = {str(k): float(v) for k, v in fi0.items()}
                order_idx = _order_indices_by_gain(full_names, gain_map)
                base_csv = out_root / "baseline_feature_importance.csv"
                pd.DataFrame(
                    {"feature": list(gain_map.keys()), "importance_gain": list(gain_map.values())}
                ).to_csv(base_csv, index=False)
                print(f"已从首档全量训练写出 gain: {base_csv}", file=sys.stderr)

        try:
            sub_rel = sub_out.relative_to(out_root)
        except ValueError:
            sub_rel = sub_out
        row: dict = {
            "tail_remove_pct": pct,
            "n_features": n_feat,
            "n_dropped": n_drop,
            "experiment_name": exp,
            "artifact_subdir": str(sub_rel),
            "end_total_return": end_tr,
        }
        rows.append(row)
        print(f"  end_total_return={end_tr}", file=sys.stderr)

    sweep_csv = out_root / "tail_feature_sweep.csv"
    pd.DataFrame(rows).to_csv(sweep_csv, index=False)
    print(f"已写入: {sweep_csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
