"""训练 → 回测 → 落盘 的编排（供 ``scripts.qlib.run_backtest`` / ``__main__`` 子命令调用）。"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd
from qlib.workflow import R
from qlib.workflow.record_temp import PortAnaRecord, SigAnaRecord, SignalRecord

from scripts.qlib.backtest.config import build_port_config_from_args
from scripts.qlib.dataset import build_training_dataset
from scripts.qlib.dataset.dump_train_matrix import dump_train_segment_csv
from scripts.qlib.runtime.constants import normalize_writable_path
from scripts.qlib.model import feature_importance_for_export, fit_model_generate_pred
from scripts.qlib.viz.feature_tail_diag import write_feature_tail_diag_csv
from scripts.qlib.viz.recorder_viz import account_total_return_from_recorder, visualize_from_recorder
from scripts.qlib.viz.segment_ic import write_segment_ic_csv


def _attach_strategy_daily_log_csv(port_config: dict[str, Any], out_dir: Path) -> None:
    """将每日策略决策 CSV 路径写入 ``port_config``，并在新回测开始前清空旧文件。"""
    path = out_dir / "strategy_daily_log.csv"
    try:
        strat = port_config.get("strategy")
        if not isinstance(strat, dict):
            return
        kw = strat.setdefault("kwargs", {})
        if not isinstance(kw, dict):
            return
        kw["strategy_daily_log_csv"] = str(path)
        if path.exists():
            path.unlink()
    except OSError:
        pass


def _run_qlib_record_backtest(
    model: Any,
    dataset: Any,
    port_config: dict[str, Any],
    recorder: Any,
    *,
    signal_ana_long_short: bool = True,
) -> dict[str, Any] | None:
    """``SignalRecord`` → ``SigAnaRecord`` → ``PortAnaRecord``；返回 ``PortAnaRecord.generate()`` 的字典。"""
    SignalRecord(model=model, dataset=dataset, recorder=recorder).generate()
    SigAnaRecord(recorder=recorder, ana_long_short=signal_ana_long_short).generate()
    out = PortAnaRecord(recorder=recorder, config=port_config).generate()
    return out if isinstance(out, dict) else None


def run_backtest_pipeline(
    args: argparse.Namespace,
    *,
    experiment_name: str | None = None,
    output_dir: Path | str | None = None,
    signal_ana_long_short: bool = True,
    model: Any | None = None,
    dataset: Any | None = None,
    port_config: dict[str, Any] | None = None,
) -> tuple[Any, float | None]:
    """单轮回测编排（唯一入口）。

    - **默认**：按 ``args`` 构建 ``Dataset``、``port_config``，在 ``R.start`` 内训练模型，再跑 Record 链与可视化。
    - **若传入** ``model`` / ``dataset`` / ``port_config`` 三者：跳过构建与训练，仅跑 Record 链（如 ``search_topk``）。
    - **若仅传入** ``dataset``（``model`` / ``port_config`` 均为 ``None``）：在该数据集上训练并回测（如 ``sweep_tail_features`` 子集）；须由调用方预先构造 ``Dataset``，不接受 ``feature_config`` 元组参数。

    返回 ``(model, portfolio_total_return)``。后者由 recorder 内 ``account`` 列推算（末/初 − 1）。
    不需要模型时用 ``_, ret = run_backtest_pipeline(...)``。

    须已由调用方执行 ``init_qlib_for_backtest``。
    """
    only_backtest = model is not None

    if only_backtest:
        if dataset is None or port_config is None:
            raise ValueError("仅回测模式须同时传入 model、dataset、port_config")
    else:
        if port_config is not None:
            raise ValueError("训练模式下不得传入 port_config")
        if dataset is None:
            dataset = build_training_dataset(args)
        port_config = build_port_config_from_args(args)

    exp = experiment_name if experiment_name is not None else args.experiment_name
    out_dir = (
        normalize_writable_path(output_dir)
        if output_dir is not None
        else normalize_writable_path(args.output_dir)
    )
    _attach_strategy_daily_log_csv(port_config, out_dir)

    print(
        "回测: SignalRecord → SigAnaRecord → PortAnaRecord；"
        f"deal_price={port_config['backtest']['exchange_kwargs']['deal_price']}",
        flush=True,
    )

    if not only_backtest and getattr(args, "dump_train_csv", False):
        fp, lp = dump_train_segment_csv(dataset, out_dir)
        print(f"已导出 train 矩阵供核对: {fp}\n{lp}", flush=True)

    with R.start(experiment_name=exp):
        if not only_backtest:
            model = fit_model_generate_pred(args, dataset)
        seg_csv = write_segment_ic_csv(
            model,
            dataset,
            out_dir / "segment_ic_stats.csv",
        )
        if seg_csv is not None:
            print(f"已写入分段 IC 诊断: {seg_csv}", flush=True)
        recorder = R.get_recorder()
        _ = _run_qlib_record_backtest(
            model,
            dataset,
            port_config,
            recorder,
            signal_ana_long_short=signal_ana_long_short,
        )
        viz_paths = visualize_from_recorder(recorder, out_dir)
        portfolio_total_return = account_total_return_from_recorder(recorder)
    print(f"Record 可视化已写入 {len(viz_paths)} 个文件 → {out_dir / 'record_viz'}", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    if portfolio_total_return is None:
        print("警告: 无法从 recorder 的 portfolio report 推算区间总收益（account 列）。", flush=True)

    if model.model is not None:
        fi = feature_importance_for_export(model, dataset=dataset, importance_type="gain")
        if fi is not None and len(fi) > 0:
            fi_path = out_dir / "feature_importance.csv"
            pd.DataFrame(
                {"feature": fi.index.astype(str), "importance_gain": fi.values}
            ).to_csv(fi_path, index=False)
            print(f"已写入: {fi_path}", flush=True)
        else:
            print(
                "警告: 无法导出 feature_importance（get_feature_importance 为空或与数据集列名无法对齐）。",
                flush=True,
            )

    tail_diag = out_dir / "feature_importance.csv"
    tail_out = write_feature_tail_diag_csv(tail_diag, out_dir / "feature_importance_tail_diag.csv")
    if tail_out is not None:
        print(f"已写入特征长尾诊断: {tail_out}", flush=True)

    print(f"完成。输出目录: {out_dir}", flush=True)

    return model, portfolio_total_return
