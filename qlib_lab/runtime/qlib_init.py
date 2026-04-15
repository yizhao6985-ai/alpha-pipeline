"""``qlib.init`` 与标的池校验。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from qlib.constant import REG_CN

from qlib_lab.provider_uri import resolve_provider_uri
from qlib_lab.runtime.constants import PROJECT_ROOT
from qlib_lab.runtime.mlflow import fixed_mlflow_exp_manager


def init_qlib_for_backtest(args: argparse.Namespace) -> str:
    """``qlib.init``、标的池文件检查；返回 resolve 后的 ``provider_uri`` 字符串。"""
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    import qlib

    uri = resolve_provider_uri(args.provider_uri)
    qlib.init(
        provider_uri=uri,
        region=REG_CN,
        exp_manager=fixed_mlflow_exp_manager(),
    )

    _inst_path = Path(uri) / "instruments" / f"{args.instruments}.txt"
    if not _inst_path.is_file():
        raise SystemExit(
            f"标的池文件不存在: {_inst_path}\n"
            "请确认已下载对应指数权重（如 data/<日期>/index/index_weight/），并重新运行 scripts/process_to_qlib.py。"
        )

    return str(uri)
