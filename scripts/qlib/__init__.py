"""
与 **Qlib 工作流**相关的实现：DataHandler、Dataset、模型、策略、回测封装、运行时初始化等。

**入口**：``python -m scripts.qlib <子命令>``（见 ``__main__.py``），或直接
``python -m scripts.qlib.run_backtest``；仓库根 ``scripts/run_backtest.py`` 等为薄转发。

库内按子目录引用，例如 ``from scripts.qlib.handler import lab_fixed_feature_config``。

若环境已安装 ``gymnasium``，在此注册 ``gym`` → ``gymnasium`` 别名（未安装则跳过，避免拖垮整包导入）。
"""
from __future__ import annotations


def _alias_gym_to_gymnasium() -> None:
    import sys

    if "gym" in sys.modules:
        return
    try:
        import gymnasium
    except ModuleNotFoundError:
        return

    sys.modules["gym"] = gymnasium


_alias_gym_to_gymnasium()
