"""将 ``backtest_daily`` 返回的报表与持仓原始表落盘，便于人工查看。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


def _safe_stem(key: str) -> str:
    s = re.sub(r"[^\w.\-]+", "_", str(key).strip(), flags=re.UNICODE)
    return s[:120] if len(s) > 120 else s


def _save_qlib_hist_positions(hist: dict[Any, Any], out_dir: Path) -> None:
    """Qlib ``Account.get_hist_positions()``：``Dict[Timestamp, BasePosition]``，转为 CSV。"""
    long_rows: list[dict[str, Any]] = []
    acc_rows: list[dict[str, Any]] = []

    def _ts_key(x: Any) -> pd.Timestamp:
        return pd.Timestamp(x)

    for ts in sorted(hist.keys(), key=_ts_key):
        pos = hist[ts]
        try:
            cash = float(pos.get_cash()) if hasattr(pos, "get_cash") else float("nan")
            stock_val = (
                float(pos.calculate_stock_value()) if hasattr(pos, "calculate_stock_value") else float("nan")
            )
            acct_val = float(pos.calculate_value()) if hasattr(pos, "calculate_value") else float("nan")
        except (TypeError, ValueError, KeyError):
            cash, stock_val, acct_val = float("nan"), float("nan"), float("nan")

        acc_rows.append(
            {
                "date": ts,
                "cash": cash,
                "stock_value": stock_val,
                "account_value": acct_val,
            }
        )

        if not hasattr(pos, "get_stock_weight_dict"):
            continue
        try:
            wmap = pos.get_stock_weight_dict(only_stock=False)
            amap = pos.get_stock_amount_dict() if hasattr(pos, "get_stock_amount_dict") else {}
        except (TypeError, ValueError, KeyError):
            continue
        for sid in sorted(set(wmap.keys()) | set(amap.keys())):
            long_rows.append(
                {
                    "date": ts,
                    "instrument": sid,
                    "weight": wmap.get(sid, float("nan")),
                    "amount": amap.get(sid, float("nan")),
                }
            )

    if acc_rows:
        pd.DataFrame(acc_rows).to_csv(out_dir / "positions_normal_account.csv", index=False)
    if long_rows:
        pd.DataFrame(long_rows).to_csv(out_dir / "positions_normal_long.csv", index=False)


def save_backtest_raw_outputs(
    report_normal: Any,
    positions_normal: Any,
    out_dir: Path,
) -> None:
    """写入 ``report_normal.csv``。

    持仓：
    - Qlib 常见为 ``Dict[Timestamp, BasePosition]`` → ``positions_normal_account.csv``、``positions_normal_long.csv``；
    - 单个 ``DataFrame`` → ``positions_normal.csv``；
    - ``dict`` 且值为 ``DataFrame`` → ``positions_normal_<key>.csv``。
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if report_normal is not None and isinstance(report_normal, pd.DataFrame) and not report_normal.empty:
        report_normal.to_csv(out_dir / "report_normal.csv", index=True)

    if positions_normal is None:
        return
    if isinstance(positions_normal, pd.DataFrame):
        if not positions_normal.empty:
            positions_normal.to_csv(out_dir / "positions_normal.csv", index=True)
        return
    if isinstance(positions_normal, dict):
        if not positions_normal:
            return
        first = next(iter(positions_normal.values()))
        if isinstance(first, pd.DataFrame):
            for key, val in positions_normal.items():
                if not isinstance(val, pd.DataFrame) or val.empty:
                    continue
                stem = _safe_stem(str(key))
                val.to_csv(out_dir / f"positions_normal_{stem}.csv", index=True)
            return
        if hasattr(first, "get_stock_weight_dict"):
            _save_qlib_hist_positions(positions_normal, out_dir)
