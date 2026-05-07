"""
收盘调仓 TopK：与标签 ``Ref($close,-1)/$close-1``（次日收盘相对当日收盘）一致时，须 ``deal_price=("$close", "$close")``。

每个交易日：
 1. 在预测分全市场降序序列上先丢弃头部 **n_drop** 名（默认 1，可调为 0），再从中取 **TopK**
    为当日目标池；用于弱化「最靠前预测」的拥挤交易（与 Qlib ``TopkDropoutStrategy`` 的 ``n_drop``
    名称一致，但此处为**确定性头部剔除**，非随机 dropout）。
 2. **卖**：仅对**不在**当日 TopK 的持仓做**整只平仓**；不对 TopK 内仓位做减仓/补仓。
 3. **腾坑**：上述平仓且 ``check_order`` 成交的笔数 = 可用新开栏位数。
 4. **买（仅开仓，无补仓）**：在 TopK 中、当前仍**零持仓**的标的按排名列出。若当日有腾坑，则取头部
    ``min(腾坑数, 待开仓数)`` 只；若无腾坑且 TopK 内**从未有过**持股，则首轮按排名建满零头寸；若无腾坑但持仓未满 ``topk``（仍有「空位」），则按排名补未建仓标的。仅对上述 ``n`` 只**新开仓**将**当前可用现金**等额分为 ``per = cash/n`` 入账（受最小调仓门槛约束）。
 5. 日志中的等权目标市值仍以 ``deploy/topk`` 记录，仅作参考，**不驱动**买入规模。

回测需在 ``Exchange`` 中设置 ``deal_price=(买入价, 卖出价)=("$close", "$close")``。
训练标签与价格均以 **当日收盘** 为参照时，预测分数天然与「当日收盘调仓」同一交易日；
``BaseSignalStrategy`` 取信号仍会带 ``shift=1`` 的旧惯例，本类用日历补丁把该 ``shift=1`` 映射为当日，避免多移一天。
"""

from __future__ import annotations

import copy
import csv
from pathlib import Path

import pandas as pd

from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.contrib.strategy.signal_strategy import BaseSignalStrategy

from scripts.qlib.runtime.constants import normalize_writable_path

_STRATEGY_LOG_FIELDS = [
    "trade_date",
    "trade_start_time",
    "trade_end_time",
    "status",
    "nav",
    "target_deploy",
    "min_rebalance_ticket",
    "risk_degree",
    "topk_codes",
    "topk_weights",
    "n_sell_orders",
    "n_buy_orders",
    "sell_shares_total",
    "buy_shares_total",
]


class OvernightTopkStrategy(BaseSignalStrategy):
    """TopK 日更、只平非 TopK；腾坑后按头部开新仓；现金等额分；无补仓。"""

    def __init__(
        self,
        *,
        topk: int = 4,
        n_drop: int = 1,
        only_tradable: bool = True,
        forbid_all_trade_at_limit: bool = False,
        strategy_daily_log_csv: str | Path | None = None,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        topk
            每个调仓日最多持有的股票数量；在预测分排序后取前 ``topk`` 只。
        n_drop
            在按预测分降序排队后、入选 TopK **之前**丢弃的名次数（默认 1）。为 0 时不丢弃。
        only_tradable
            为 True 时，买入候选会跳过当日不可交易标的（仅影响建仓名单，不影响已持仓卖出逻辑）。
        forbid_all_trade_at_limit
            传给 ``is_stock_tradable``：涨跌停时是否禁止该方向成交（与 Qlib 默认行为一致，需与回测配置一起看）。
        strategy_daily_log_csv
            若给定路径，每个交易日将决策摘要追加写入该 CSV（回测编排层按 ``output_dir`` 传入）。
        """
        super().__init__(**kwargs)
        self.topk = int(topk)
        self.n_drop = int(n_drop)
        self.only_tradable = only_tradable
        self.forbid_all_trade_at_limit = forbid_all_trade_at_limit
        self._strategy_daily_log_csv: Path | None = (
            normalize_writable_path(strategy_daily_log_csv)
            if strategy_daily_log_csv
            else None
        )

    def generate_trade_decision(self, execute_result=None):
        """
        标签已按 close 定义时，信号与收盘调仓 **无需** 再人为错开一日。
        但 ``BaseSignalStrategy`` 内部仍会使用 ``shift=1`` 取预测时间窗；此处把
        ``get_step_time(..., shift=1)`` 临时等同于 ``shift=0``，仅在本轮决策内生效，
        使取到的预测与当前 ``trade_step`` 同一天。
        """
        cal = self.trade_calendar
        orig_get_step_time = cal.get_step_time

        def get_step_time_same_day(trade_step=None, shift=0):
            # 抵消父类对预测时间的 shift=1，与「close 标签 / 收盘撮合」同日对齐
            if shift == 1:
                shift = 0
            return orig_get_step_time(trade_step, shift=shift)

        cal.get_step_time = get_step_time_same_day
        try:
            return self._decision(execute_result)
        finally:
            cal.get_step_time = orig_get_step_time

    def _deal_price(self, code: str, trade_start_time, trade_end_time) -> float | None:
        p = self.trade_exchange.get_deal_price(
            stock_id=code,
            start_time=trade_start_time,
            end_time=trade_end_time,
            direction=OrderDir.BUY,
        )
        if p is None or (isinstance(p, float) and p <= 1e-8):
            return None
        return float(p)

    def _position_value(
        self,
        code: str,
        amount: float,
        trade_start_time,
        trade_end_time,
    ) -> float:
        if amount <= 0:
            return 0.0
        p = self._deal_price(code, trade_start_time, trade_end_time)
        if p is None:
            return 0.0
        return float(amount) * p

    @staticmethod
    def _min_rebalance_ticket(nav: float, target_deploy: float) -> float:
        """由当日总权益与目标多头市值推算最小有效调仓金额（元），抑制碎单、随规模缩放。"""
        n = max(0.0, float(nav))
        d = max(0.0, float(target_deploy))
        return max(15.0, 5e-5 * n, 2e-4 * d)

    def _append_strategy_daily_log(self, row: dict[str, object]) -> None:
        if self._strategy_daily_log_csv is None:
            return
        path = self._strategy_daily_log_csv
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=_STRATEGY_LOG_FIELDS, extrasaction="ignore")
            if write_header:
                w.writeheader()
            w.writerow({k: row.get(k, "") for k in _STRATEGY_LOG_FIELDS})

    def _decision(self, execute_result=None):
        """先平非 TopK；再按腾坑/首轮建仓开仓，等额使用可用现金。"""
        trade_step = self.trade_calendar.get_trade_step()
        trade_start_time, trade_end_time = self.trade_calendar.get_step_time(trade_step)
        pred_start_time, pred_end_time = self.trade_calendar.get_step_time(
            trade_step, shift=1
        )
        pred_score = self.signal.get_signal(
            start_time=pred_start_time, end_time=pred_end_time
        )
        if isinstance(pred_score, pd.DataFrame):
            pred_score = pred_score.iloc[:, 0]
        if pred_score is None or len(pred_score.dropna()) == 0:
            self._append_strategy_daily_log(
                {
                    "trade_date": str(trade_start_time)[:10],
                    "trade_start_time": str(trade_start_time),
                    "trade_end_time": str(trade_end_time),
                    "status": "no_signal",
                }
            )
            return TradeDecisionWO([], self)

        ranked = pred_score.dropna().sort_values(ascending=False)
        nd = min(max(0, self.n_drop), len(ranked))
        if nd:
            ranked = ranked.iloc[nd:]
        if len(ranked) == 0:
            self._append_strategy_daily_log(
                {
                    "trade_date": str(trade_start_time)[:10],
                    "trade_start_time": str(trade_start_time),
                    "trade_end_time": str(trade_end_time),
                    "status": "no_signal_after_n_drop",
                }
            )
            return TradeDecisionWO([], self)

        buy_codes: list[str] = []
        for code in ranked.index:
            if len(buy_codes) >= self.topk:
                break
            if self.only_tradable and not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
            ):
                continue
            if not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
            ):
                continue
            buy_codes.append(code)

        if not buy_codes:
            self._append_strategy_daily_log(
                {
                    "trade_date": str(trade_start_time)[:10],
                    "trade_start_time": str(trade_start_time),
                    "trade_end_time": str(trade_end_time),
                    "status": "no_tradable_topk",
                }
            )
            return TradeDecisionWO([], self)

        k = len(buy_codes)
        eq = 1.0 / k
        target_w = {c: eq for c in buy_codes}

        current_temp = copy.deepcopy(self.trade_position)
        cash0 = float(current_temp.get_cash())

        nav = cash0
        for code in list(current_temp.get_stock_list()):
            amt = float(current_temp.get_stock_amount(code=code))
            nav += self._position_value(code, amt, trade_start_time, trade_end_time)

        target_deploy = float(nav) * float(self.get_risk_degree(trade_step))
        min_rb = self._min_rebalance_ticket(nav, target_deploy)
        buy_set = set(buy_codes)

        sell_orders: list[Order] = []
        # 仅「整只卖出不在当日 TopK」且成交：记为腾坑
        n_slots_freed = 0

        # ---------- 卖出：仅平仓非 TopK，不减仓 TopK 内超配 ----------
        for code in list(current_temp.get_stock_list()):
            if code in buy_set:
                continue
            if not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=None if self.forbid_all_trade_at_limit else OrderDir.SELL,
            ):
                continue
            sell_amt = float(current_temp.get_stock_amount(code=code))
            if sell_amt <= 0:
                continue
            order = Order(
                stock_id=code,
                amount=sell_amt,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=Order.SELL,
            )
            if self.trade_exchange.check_order(order):
                sell_orders.append(order)
                _, _, _ = self.trade_exchange.deal_order(
                    order, position=current_temp
                )
                n_slots_freed += 1

        # ---------- 买入：仅新开仓；现金等额分；无补仓 ----------
        cash_avail = float(current_temp.get_cash())

        zeros_ordered = [
            c
            for c in buy_codes
            if float(current_temp.get_stock_amount(code=c)) <= 1e-12
        ]
        held_any_topk = any(
            float(current_temp.get_stock_amount(code=c)) > 1e-12 for c in buy_codes
        )

        n_hold_topk = sum(
            1
            for c in buy_codes
            if float(current_temp.get_stock_amount(code=c)) > 1e-12
        )
        room = max(0, self.topk - n_hold_topk)

        if n_slots_freed > 0:
            to_open = zeros_ordered[: min(len(zeros_ordered), n_slots_freed)]
        elif not held_any_topk and zeros_ordered:
            # 首轮：TopK 内尚未有任何持股，按排名一次建满（或尽可能多的）零头寸
            to_open = zeros_ordered
        elif room > 0 and zeros_ordered:
            # 无新腾坑，但当前 TopK 持仓未满 topk 只：用可用现金按排名补齐未建仓标的（非补仓）
            to_open = zeros_ordered[: min(len(zeros_ordered), room)]
        else:
            to_open = []

        buy_orders: list[Order] = []
        if to_open:
            n_b = len(to_open)
            per_cash = cash_avail / n_b
            if per_cash >= min_rb:
                for code in to_open:
                    if not self.trade_exchange.is_stock_tradable(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=None
                        if self.forbid_all_trade_at_limit
                        else OrderDir.BUY,
                    ):
                        continue
                    p = self._deal_price(code, trade_start_time, trade_end_time)
                    if p is None:
                        continue
                    buy_amount = per_cash / p
                    factor = self.trade_exchange.get_factor(
                        stock_id=code,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                    )
                    buy_amount = self.trade_exchange.round_amount_by_trade_unit(
                        buy_amount, factor
                    )
                    if buy_amount <= 0:
                        continue
                    order = Order(
                        stock_id=code,
                        amount=buy_amount,
                        start_time=trade_start_time,
                        end_time=trade_end_time,
                        direction=Order.BUY,
                    )
                    if self.trade_exchange.check_order(order):
                        buy_orders.append(order)

        sell_shares_total = sum(float(o.amount) for o in sell_orders)
        buy_shares_total = sum(float(o.amount) for o in buy_orders)
        weights_str = ";".join(
            f"{c}:{target_w[c]:.6f}" for c in buy_codes
        )
        self._append_strategy_daily_log(
            {
                "trade_date": str(trade_start_time)[:10],
                "trade_start_time": str(trade_start_time),
                "trade_end_time": str(trade_end_time),
                "status": "ok",
                "nav": f"{nav:.6f}",
                "target_deploy": f"{target_deploy:.6f}",
                "min_rebalance_ticket": f"{min_rb:.6f}",
                "risk_degree": f"{float(self.get_risk_degree(trade_step)):.6f}",
                "topk_codes": ";".join(buy_codes),
                "topk_weights": weights_str,
                "n_sell_orders": len(sell_orders),
                "n_buy_orders": len(buy_orders),
                "sell_shares_total": f"{sell_shares_total:.6f}",
                "buy_shares_total": f"{buy_shares_total:.6f}",
            }
        )

        return TradeDecisionWO(sell_orders + buy_orders, self)
