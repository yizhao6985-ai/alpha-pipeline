"""行业 / 组内中性化（扩展点，默认主流程未启用）。

在截面预测中，估值与规模常驱动「风格」而非可交易 alpha。常见做法是在特征或预测上对
行业、市值等因子做回归残差或组内去均值（Qlib 社区与 ``processor`` 模块中的截面算子可组合使用）。

**当前仓库** 的 ``lab_fixed_features`` 未要求行业分类列；若后续在 ``QlibDataLoader`` 的 feature 中增加
行业标签，可在 :func:`scripts.qlib.handler.processors.default_infer_processors`
之前插入自定义 ``Processor``，且 ``fit_start_time`` / ``fit_end_time`` 必须仅限 train 段以防泄露。

参见 Qlib ``qlib.data.dataset.processor`` 中 ``CSZScoreNorm``、``CSRankNorm`` 等截面算子。
"""
from __future__ import annotations
