"""训练 → 回测 → 落盘 的编排（供 ``scripts.qlib.run_backtest`` / ``__main__`` 子命令调用）。"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from qlib.workflow import R

from scripts.qlib.backtest.config import build_port_config_from_args
from scripts.qlib.backtest.daily_runner import backtest_daily_with_trained
from scripts.qlib.backtest.plotting import save_backtest_analysis
from scripts.qlib.backtest.raw_export import save_backtest_raw_outputs
from scripts.qlib.dataset import build_training_dataset
from scripts.qlib.model import fit_model_generate_pred


def run_backtest_save_artifacts(
    args: argparse.Namespace,
    *,
    model: Any,
    dataset: Any,
    port_config: dict[str, Any],
    output_dir: Path | str,
) -> tuple[pd.DataFrame | None, Any]:
    """对已训练 ``model`` 执行 ``backtest_daily`` 并写入落盘产物。

    须已由调用方执行 ``init_qlib_for_backtest``；不负责训练或 ``R.start``。
    """
    out_dir = Path(output_dir).expanduser().resolve()

    print(
        "回测: backtest_daily + OvernightTopkStrategy；"
        f"deal_price={port_config['backtest']['exchange_kwargs']['deal_price']}",
        flush=True,
    )

    report_normal, positions_normal = backtest_daily_with_trained(model, dataset, port_config)

    out_dir.mkdir(parents=True, exist_ok=True)

    save_backtest_raw_outputs(report_normal, positions_normal, out_dir)
    print(
        f"已写入原始回测表: {out_dir / 'report_normal.csv'}；"
        f"持仓见 positions_normal_account.csv / positions_normal_long.csv（或 positions_normal*.csv）",
        flush=True,
    )

    if report_normal is not None and isinstance(report_normal, pd.DataFrame) and not report_normal.empty:
        save_backtest_analysis(report_normal, out_dir)
        print(
            f"已写入绩效: {out_dir / 'risk_metrics.csv'}；"
            f"图: cumulative_return.png, drawdown.png, monthly_return_heatmap.png",
            flush=True,
        )
    else:
        print("警告: backtest_daily 未返回可用的 report_normal。", flush=True)

    if model.model is not None:
        fi = model.get_feature_importance(importance_type="gain")
        fi_path = out_dir / "feature_importance.csv"
        pd.DataFrame(
            {"feature": fi.index.astype(str), "importance_gain": fi.values}
        ).to_csv(fi_path, index=False)
        print(f"已写入: {fi_path}", flush=True)
        print(
            "提示: 若需按 gain 截取特征，可例如 "
            f"--feature-top-k 100 --feature-importance-csv {fi_path}",
            flush=True,
        )

    print(f"完成。输出目录: {out_dir}", flush=True)
    return report_normal, positions_normal


def run_backtest_pipeline(
    args: argparse.Namespace,
    *,
    feature_config: tuple[list[str], list[str]] | None = None,
    experiment_name: str | None = None,
    output_dir: Path | str | None = None,
) -> tuple[Any, pd.DataFrame | None, Any, Any]:
    """单轮：构建 Dataset → 训练 → 回测 → 写表 / 图 / feature_importance。

    须已由调用方执行 ``init_qlib_for_backtest``。
    """
    dataset = build_training_dataset(args, feature_config=feature_config)
    port_config = build_port_config_from_args(args)
    exp = experiment_name if experiment_name is not None else args.experiment_name
    out_dir = Path(output_dir).expanduser().resolve() if output_dir is not None else args.output_dir.resolve()

    with R.start(experiment_name=exp):
        model = fit_model_generate_pred(args, dataset)

    report_normal, positions_normal = run_backtest_save_artifacts(
        args,
        model=model,
        dataset=dataset,
        port_config=port_config,
        output_dir=out_dir,
    )
    return model, report_normal, positions_normal, dataset
