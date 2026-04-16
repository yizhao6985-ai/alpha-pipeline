#!/usr/bin/env python3
"""
按 LightGBM gain 从尾部按累计剔除比例做网格；单轮编排见 ``scripts.qlib.backtest.pipeline.run_backtest_pipeline``。

::

    python -m scripts.qlib sweep_tail_features --tail-min-pct 0 --tail-max-pct 30 --tail-step-pct 5
    python -m scripts.qlib.sweep_tail_features
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from scripts.qlib.backtest.daily_runner import end_total_return_from_report_normal
from scripts.qlib.backtest.pipeline import run_backtest_pipeline
from scripts.qlib.cli.backtest_args import build_arg_parser
from scripts.qlib.handler import full_feature_config_unpruned
from scripts.qlib.handler.features.importance_pick import order_indices_by_gain
from scripts.qlib.runtime import init_qlib_for_backtest


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


def parse_sweep_args():
    p = build_arg_parser()
    g = p.add_argument_group("尾部特征剔除网格（本模块）")
    g.add_argument(
        "--money-stack-days",
        type=int,
        default=20,
        metavar="N",
        help="成交额堆叠长度（含当日），与 ``full_feature_config_unpruned`` 一致；例如 60 为长堆叠",
    )
    g.add_argument(
        "--max-features",
        type=int,
        default=0,
        metavar="K",
        help="按 gain 仅保留前 K 列（须配合 --feature-importance-csv）；默认 0 为全量列",
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
        "--sweep-subdir-prefix",
        type=str,
        default="tail",
        help="各档输出子目录名前缀：{prefix}_{pct}/；bootstrap 为 {prefix}_bootstrap/",
    )
    return p.parse_args()


def main() -> int:
    args = parse_sweep_args()
    out_root = args.output_dir.expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    grid = _tail_pct_grid(args.tail_min_pct, args.tail_max_pct, args.tail_step_pct)

    init_qlib_for_backtest(args)

    if args.money_stack_days < 1:
        raise SystemExit("--money-stack-days 须 >= 1")
    max_feat = None if args.max_features <= 0 else args.max_features
    full_fields, full_names = full_feature_config_unpruned(
        money_stack_days=args.money_stack_days,
        max_features=max_feat,
        importance_csv=args.feature_importance_csv,
    )
    n_full = len(full_names)
    if n_full == 0:
        raise SystemExit("全量特征为空")

    prefix = args.sweep_subdir_prefix
    boot_exp = f"{args.experiment_name}_{prefix}_bootstrap".replace(".", "_")
    boot_out = out_root / f"{prefix}_bootstrap"
    print("--- bootstrap: 全量特征训练并回测，用于 gain 排序 ---", file=sys.stderr)
    model_b, report_b, _, _ = run_backtest_pipeline(
        args,
        feature_config=(full_fields, full_names),
        experiment_name=boot_exp,
        output_dir=boot_out,
    )
    if model_b.model is None:
        raise SystemExit("bootstrap 未得到模型，无法计算 feature importance")
    fi0 = model_b.get_feature_importance(importance_type="gain")
    gain_map = {str(k): float(v) for k, v in fi0.items()}
    order_idx = order_indices_by_gain(full_names, gain_map)
    base_csv = out_root / "baseline_feature_importance.csv"
    pd.DataFrame(
        {"feature": list(gain_map.keys()), "importance_gain": list(gain_map.values())}
    ).to_csv(base_csv, index=False)
    print(f"已写出 gain 基准: {base_csv}", file=sys.stderr)

    boot_end_tr = end_total_return_from_report_normal(report_b)
    rows: list[dict] = []

    for pct in grid:
        n_drop = int(n_full * float(pct) / 100.0)
        n_drop = min(max(0, n_drop), n_full - 1)
        n_feat = n_full - n_drop
        print(f"--- tail_remove_pct={pct}% 保留 {n_feat}/{n_full} 列（剔除 {n_drop}）---", file=sys.stderr)

        if abs(float(pct)) < 1e-12:
            try:
                sub_rel = boot_out.relative_to(out_root)
            except ValueError:
                sub_rel = boot_out
            rows.append(
                {
                    "tail_remove_pct": pct,
                    "n_features": n_feat,
                    "n_dropped": n_drop,
                    "experiment_name": boot_exp,
                    "artifact_subdir": str(sub_rel),
                    "end_total_return": boot_end_tr,
                }
            )
            print(f"  end_total_return={boot_end_tr}（复用 bootstrap，与 tail_0 等价）", file=sys.stderr)
            continue

        sub_f, sub_n = _subset_by_tail_pct(full_fields, full_names, order_idx, pct)
        exp = f"{args.experiment_name}_{prefix}_{pct:g}".replace(".", "_")
        sub_out = out_root / f"{prefix}_{pct:g}".replace(".", "_")
        sub_out.mkdir(parents=True, exist_ok=True)

        _, report_normal, _, _ = run_backtest_pipeline(
            args,
            feature_config=(sub_f, sub_n),
            experiment_name=exp,
            output_dir=sub_out,
        )
        end_tr = end_total_return_from_report_normal(report_normal)

        try:
            sub_rel = sub_out.relative_to(out_root)
        except ValueError:
            sub_rel = sub_out
        rows.append(
            {
                "tail_remove_pct": pct,
                "n_features": n_feat,
                "n_dropped": n_drop,
                "experiment_name": exp,
                "artifact_subdir": str(sub_rel),
                "end_total_return": end_tr,
            }
        )
        print(f"  end_total_return={end_tr}", file=sys.stderr)

    sweep_csv = out_root / "tail_feature_sweep.csv"
    pd.DataFrame(rows).to_csv(sweep_csv, index=False)
    print(f"已写入: {sweep_csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
