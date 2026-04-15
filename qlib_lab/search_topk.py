#!/usr/bin/env python3
"""
训练一次模型，对多个 ``topk`` 依次执行 ``backtest_daily``，按 **区间总收益**（``report_normal`` 中 ``account`` 末/初 − 1）
选取最优 ``topk``。

用法（与 ``run_qlib_backtest`` 共用参数）::

    python -m qlib_lab.search_topk
    python -m qlib_lab.search_topk --topks 1,3,5,10,20
    python -m qlib_lab.search_topk --topk-min 2 --topk-max 30 --topk-step 2
"""
from __future__ import annotations

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
from qlib_lab.runtime import init_qlib_for_backtest
from qlib_lab.strategy import build_strategy_config_from_args
from qlib_lab.training import fit_model_generate_pred


def parse_sweep_args():
    p = build_arg_parser()
    g = p.add_argument_group("topk 网格（仅本模块）")
    g.add_argument(
        "--topks",
        type=str,
        default=None,
        help="逗号分隔，如 1,3,5,10；指定时忽略 --topk-min / --topk-max / --topk-step",
    )
    g.add_argument("--topk-min", type=int, default=1, dest="topk_min")
    g.add_argument("--topk-max", type=int, default=20, dest="topk_max")
    g.add_argument("--topk-step", type=int, default=1, dest="topk_step")
    return p.parse_args()


def resolve_topk_list(args) -> list[int]:
    if args.topks:
        out: list[int] = []
        for part in args.topks.split(","):
            s = part.strip()
            if s:
                out.append(int(s))
        if not out:
            raise SystemExit("--topks 解析结果为空")
        return out
    if args.topk_step <= 0:
        raise SystemExit("--topk-step 须为正整数")
    if args.topk_max < args.topk_min:
        raise SystemExit("--topk-max 须 >= --topk-min")
    return list(range(args.topk_min, args.topk_max + 1, args.topk_step))


def main() -> int:
    args = parse_sweep_args()
    out_dir = args.output_dir.resolve()
    topks = resolve_topk_list(args)
    init_qlib_for_backtest(args)
    dataset = build_training_dataset(args)
    port_config = {
        "strategy": build_strategy_config_from_args(args),
        "backtest": build_backtest_config_from_args(args),
    }

    with R.start(experiment_name=args.experiment_name):
        model = fit_model_generate_pred(args, dataset)
        print(
            "回测: backtest_daily + OvernightTopkStrategy（收盘撮合）；"
            f"deal_price={port_config['backtest']['exchange_kwargs']['deal_price']}"
        )

        rows: list[dict] = []
        for k in topks:
            port_config["strategy"]["kwargs"]["topk"] = k
            report_normal, _ = backtest_daily_with_trained(model, dataset, port_config)
            tr = end_total_return_from_report_normal(report_normal)
            rows.append({"topk": k, "end_total_return": tr})
            print(f"  topk={k}  end_total_return={tr}")

        best = max(
            rows,
            key=lambda r: r["end_total_return"]
            if r["end_total_return"] is not None
            else float("-inf"),
        )
        best_k = int(best["topk"])
        print(f"最优 topk={best_k}（end_total_return={best['end_total_return']}）")
        if best["end_total_return"] is None:
            print("警告: 未能从报表解析收益，最优 topk 仅按占位规则选取。", flush=True)

        out_dir.mkdir(parents=True, exist_ok=True)
        sweep_path = out_dir / "topk_sweep.csv"
        pd.DataFrame(rows).to_csv(sweep_path, index=False)
        print(f"已写入: {sweep_path}")

        if model.model is not None:
            fi_series = model.get_feature_importance(importance_type="gain")
            fi_csv = out_dir / "feature_importance.csv"
            pd.DataFrame(
                {"feature": fi_series.index.astype(str), "importance_gain": fi_series.values}
            ).to_csv(fi_csv, index=False)

    print(f"完成。最优 topk={best_k}；输出目录: {out_dir}（含 topk_sweep.csv）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
