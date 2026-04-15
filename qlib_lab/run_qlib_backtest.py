#!/usr/bin/env python3
"""
Qlib 基本用例：qlib_data + 全量特征 + LightGBM + 日频多头回测。

训练与 ``search_topk`` / ``sweep_tail_feature_backtest`` 共用 ``fit_model_generate_pred``（``mlruns`` 中仅训练日志）。

组合回测仅使用 ``qlib.contrib.evaluate.backtest_daily``；报表写入 ``--output-dir/qlib_backtest_report_normal.csv``，
并生成 ``report_normal.png``、``positions_normal*.png``；因子重要度写入 ``feature_importance.csv``。

默认标签 ``Ref($close,-1)/$close-1``；撮合价 ``("$close","$close")``；策略为收盘调仓 TopK。

执行::

    python -m qlib_lab.run_qlib_backtest
    python -m qlib_lab.run_qlib_backtest --provider-uri ./qlib_data --output-dir ./qlib_runs/plots
"""
from __future__ import annotations

import pandas as pd
from qlib.workflow import R

from qlib_lab.backtest import backtest_daily_with_trained, build_backtest_config_from_args
from qlib_lab.backtest.plotting import save_backtest_plots
from qlib_lab.cli.backtest import parse_args
from qlib_lab.dataset import build_training_dataset
from qlib_lab.runtime import init_qlib_for_backtest
from qlib_lab.strategy import build_strategy_config_from_args
from qlib_lab.training import fit_model_generate_pred


def main() -> int:
    args = parse_args()
    init_qlib_for_backtest(args)
    dataset = build_training_dataset(args)

    port_config = {
        "strategy": build_strategy_config_from_args(args),
        "backtest": build_backtest_config_from_args(args),
    }

    with R.start(experiment_name=args.experiment_name):
        model = fit_model_generate_pred(args, dataset)

    print(
        "回测: backtest_daily + OvernightTopkStrategy；"
        f"deal_price={port_config['backtest']['exchange_kwargs']['deal_price']}"
    )

    report_normal, positions_normal = backtest_daily_with_trained(model, dataset, port_config)

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if report_normal is not None and isinstance(report_normal, pd.DataFrame) and not report_normal.empty:
        report_path = out_dir / "qlib_backtest_report_normal.csv"
        report_normal.to_csv(report_path)
        print(f"已写入组合净值/风险报表: {report_path}")
        print(report_normal.head())
    else:
        print("警告: backtest_daily 未返回可用的 report_normal。", flush=True)

    save_backtest_plots(report_normal, positions_normal, out_dir)
    print(f"已写入图表: {out_dir / 'report_normal.png'}；持仓图见 positions_normal*.png")

    if model.model is not None:
        fi = model.get_feature_importance(importance_type="gain")
        fi_path = out_dir / "feature_importance.csv"
        pd.DataFrame(
            {"feature": fi.index.astype(str), "importance_gain": fi.values}
        ).to_csv(fi_path, index=False)
        print(f"已写入: {fi_path}")

    print(f"完成。输出目录: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
