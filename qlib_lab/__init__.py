"""
Qlib 训练与回测库。

目录约定：
  ``handler/`` — DataHandler 与特征；``dataset/`` — DatasetH；``model/`` — LightGBM
  ``strategy/`` — 策略实现与 ``port_config['strategy']``
  ``backtest/`` — 仅组合回测段配置与交易所默认值（``port_config['backtest']``）
  ``training/`` — 模型训练；``backtest/daily_runner`` — ``backtest_daily`` 封装
  ``runtime/`` — ``qlib.init``、项目路径、MLflow 实验目录
  ``cli/`` — 命令行参数；``run_qlib_backtest.py`` — 主入口 CLI

``pyqlib`` 仍依赖已停止维护的 ``gym``；在导入本包子模块前将 ``sys.modules["gym"]`` 指向 ``gymnasium``，
避免弃用提示并与 NumPy 2.x 兼容。须已安装 ``gymnasium``；若先于本包执行过 ``import gym`` 则无法替换。
"""
from __future__ import annotations


def _alias_gym_to_gymnasium() -> None:
    import sys

    if "gym" in sys.modules:
        return
    import gymnasium

    sys.modules["gym"] = gymnasium


_alias_gym_to_gymnasium()

from qlib_lab.handler import (
    DEFAULT_LABEL_EXPR,
    QuantFoundryRawFields,
    alpha158_classic_feature_config,
    alpha360_stacked_feature_config,
    build_training_handler,
    chip_feature_config,
    full_feature_config_pruned_top508,
    full_feature_config_unpruned,
    fundamental_feature_config,
    raw_market_feature_config,
)
from qlib_lab.model import LGBModel
from qlib_lab.dataset import build_dataset

__all__ = [
    "DEFAULT_LABEL_EXPR",
    "LGBModel",
    "QuantFoundryRawFields",
    "alpha158_classic_feature_config",
    "alpha360_stacked_feature_config",
    "build_dataset",
    "build_training_handler",
    "chip_feature_config",
    "full_feature_config_pruned_top508",
    "full_feature_config_unpruned",
    "fundamental_feature_config",
    "raw_market_feature_config",
]
