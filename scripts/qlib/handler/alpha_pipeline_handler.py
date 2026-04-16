"""``AlphaPipelineRawFields`` DataHandler：接 Qlib ``QlibDataLoader``。"""
from __future__ import annotations

from qlib.contrib.data.handler import _DEFAULT_LEARN_PROCESSORS, check_transform_proc
from qlib.data.dataset.handler import DataHandlerLP

from scripts.qlib.handler.features.lab_fixed_features import lab_fixed_feature_config
from scripts.qlib.handler.label import DEFAULT_LABEL_EXPR


class AlphaPipelineRawFields(DataHandlerLP):
    """默认特征为 ``handler.features.lab_fixed_features`` 中的固定列。

    未传 ``feature_config`` 时由 :func:`~scripts.qlib.handler.features.lab_fixed_features.lab_fixed_feature_config` 提供列清单。
    """

    def __init__(
        self,
        instruments: str = "csi_a500",
        start_time: str | None = None,
        end_time: str | None = None,
        freq: str = "day",
        infer_processors: list | None = None,
        learn_processors: list | None = None,
        fit_start_time: str | None = None,
        fit_end_time: str | None = None,
        process_type: str = DataHandlerLP.PTYPE_A,
        filter_pipe=None,
        inst_processors=None,
        feature_config: tuple[list[str], list[str]] | None = None,
        **kwargs,
    ) -> None:
        if infer_processors is None:
            infer_processors = []
        if learn_processors is None:
            learn_processors = list(_DEFAULT_LEARN_PROCESSORS)

        infer_processors = check_transform_proc(infer_processors, fit_start_time, fit_end_time)
        learn_processors = check_transform_proc(learn_processors, fit_start_time, fit_end_time)

        feat = feature_config if feature_config is not None else self.get_feature_config()
        data_loader = {
            "class": "QlibDataLoader",
            "kwargs": {
                "config": {
                    "feature": feat,
                    "label": kwargs.pop("label", self.get_label_config()),
                },
                "filter_pipe": filter_pipe,
                "freq": freq,
                "inst_processors": inst_processors,
            },
        }
        super().__init__(
            instruments=instruments,
            start_time=start_time,
            end_time=end_time,
            data_loader=data_loader,
            learn_processors=learn_processors,
            infer_processors=infer_processors,
            process_type=process_type,
            **kwargs,
        )

    def get_feature_config(self) -> tuple[list[str], list[str]]:
        return lab_fixed_feature_config()

    def get_label_config(self) -> tuple[list[str], list[str]]:
        return [DEFAULT_LABEL_EXPR], ["LABEL0"]
