"""固定到仓库根目录 ``mlruns`` 的 Qlib 实验管理配置。"""
from __future__ import annotations

from scripts.qlib.runtime.constants import PROJECT_ROOT


def fixed_mlflow_exp_manager() -> dict:
    """与 qlib 默认 MLflowExpManager 一致，仅将 uri 固定为 ``<项目根>/mlruns``。"""
    mlruns = (PROJECT_ROOT / "mlruns").resolve()
    return {
        "class": "MLflowExpManager",
        "module_path": "qlib.workflow.expm",
        "kwargs": {
            "uri": "file:" + str(mlruns),
            "default_exp_name": "Experiment",
        },
    }
