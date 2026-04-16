#!/usr/bin/env python3
"""
训练一次模型，对多个 ``topk`` 依次回测，按 ``report_normal`` 区间总收益选最优。

编排与 ``scripts.qlib.backtest.pipeline.run_backtest_save_artifacts`` 一致。

::

    python -m scripts.qlib search_topk
    python -m scripts.qlib.search_topk
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from qlib.workflow import R

from scripts.qlib.backtest.config import build_port_config_from_args
from scripts.qlib.backtest.daily_runner import end_total_return_from_report_normal
from scripts.qlib.backtest.pipeline import run_backtest_save_artifacts
from scripts.qlib.cli.backtest_args import build_arg_parser
from scripts.qlib.dataset import build_training_dataset
from scripts.qlib.model import fit_model_generate_pred
from scripts.qlib.runtime import init_qlib_for_backtest


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
    out_dir = args.output_dir.expanduser().resolve()
    topks = resolve_topk_list(args)
    init_qlib_for_backtest(args)
    dataset = build_training_dataset(args)
    port_config = build_port_config_from_args(args)

    with R.start(experiment_name=args.experiment_name):
        model = fit_model_generate_pred(args, dataset)

    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for k in topks:
        port_config["strategy"]["kwargs"]["topk"] = k
        sub_out = out_dir / f"topk_{k}"
        report_normal, _ = run_backtest_save_artifacts(
            args,
            model=model,
            dataset=dataset,
            port_config=port_config,
            output_dir=sub_out,
        )
        tr = end_total_return_from_report_normal(report_normal)
        try:
            sub_rel = sub_out.relative_to(out_dir)
        except ValueError:
            sub_rel = sub_out
        rows.append(
            {
                "topk": k,
                "end_total_return": tr,
                "artifact_subdir": str(sub_rel),
            }
        )
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

    sweep_path = out_dir / "topk_sweep.csv"
    pd.DataFrame(rows).to_csv(sweep_path, index=False)
    print(f"已写入: {sweep_path}")

    print(
        f"完成。最优 topk={best_k}；输出目录: {out_dir}（含 topk_sweep.csv；各档见 topk_<K>/）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
