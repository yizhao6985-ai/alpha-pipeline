"""
收盘调仓 TopK：与标签 ``Ref($close,-1)/$close-1``（次日收盘相对当日收盘）一致时，须 ``deal_price=("$close", "$close")``。

每个交易日：
 1. **增量调仓**：保留仍在 TopK 内的标的，仅卖出调出标的及对超配标的减仓；对新进或低配标的买入至目标市值，降低无谓全仓换手。
 2. **按预测分加权**：在当日 TopK 内将 ``deploy``（总权益 × ``risk_degree``）按分数分配；分数先平移到非负再归一化，避免全负时权重退化。
 3. **最小调仓门槛**：由当日总权益 ``nav`` 与目标多头规模 ``target_deploy`` 自适应推算，无需额外传参。

回测需在 ``Exchange`` 中设置 ``deal_price=(买入价, 卖出价)=("$close", "$close")``。
训练标签与价格均以 **当日收盘** 为参照时，预测分数天然与「当日收盘调仓」同一交易日；
``BaseSignalStrategy`` 取信号仍会带 ``shift=1`` 的旧惯例，本类用日历补丁把该 ``shift=1`` 映射为当日，避免多移一天。
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.contrib.strategy.signal_strategy import BaseSignalStrategy


class OvernightTopkStrategy(BaseSignalStrategy):
    """每日尾盘收盘撮合：TopK 多头、预测分加权；增量换手（非每日全卖再全买）。"""

    def __init__(
        self,
        *,
        topk: int = 4,
        only_tradable: bool = True,
        forbid_all_trade_at_limit: bool = False,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        topk
            每个调仓日最多持有的股票数量；在预测分排序后取前 ``topk`` 只。
        only_tradable
            为 True 时，买入候选会跳过当日不可交易标的（仅影响建仓名单，不影响已持仓卖出逻辑）。
        forbid_all_trade_at_limit
            传给 ``is_stock_tradable``：涨跌停时是否禁止该方向成交（与 Qlib 默认行为一致，需与回测配置一起看）。
        """
        super().__init__(**kwargs)
        self.topk = int(topk)
        self.only_tradable = only_tradable
        self.forbid_all_trade_at_limit = forbid_all_trade_at_limit

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
    def _score_weights(scores: np.ndarray) -> np.ndarray:
        """TopK 内分数平移到非负后归一化，得到资金权重（和为 1）。"""
        s = scores.astype(float)
        adj = s - np.min(s) + 1e-12
        w = adj / np.sum(adj)
        return w

    @staticmethod
    def _min_rebalance_ticket(nav: float, target_deploy: float) -> float:
        """由当日总权益与目标多头市值推算最小有效调仓金额（元），抑制碎单、随规模缩放。"""
        n = max(0.0, float(nav))
        d = max(0.0, float(target_deploy))
        return max(15.0, 5e-5 * n, 2e-4 * d)

    def _decision(self, execute_result=None):
        """增量调仓：调出/减仓先卖，再按目标加权市值买入。"""
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
            return TradeDecisionWO([], self)

        ranked = pred_score.dropna().sort_values(ascending=False)
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
            return TradeDecisionWO([], self)

        scores_top = ranked.loc[buy_codes].values.astype(float)
        weights = self._score_weights(scores_top)
        target_w = dict(zip(buy_codes, weights))

        current_temp = copy.deepcopy(self.trade_position)
        cash0 = float(current_temp.get_cash())

        nav = cash0
        for code in list(current_temp.get_stock_list()):
            amt = float(current_temp.get_stock_amount(code=code))
            nav += self._position_value(code, amt, trade_start_time, trade_end_time)

        target_deploy = float(nav) * float(self.get_risk_degree(trade_step))
        target_value = {c: target_w[c] * target_deploy for c in buy_codes}
        min_rb = self._min_rebalance_ticket(nav, target_deploy)

        sell_orders: list[Order] = []

        # ---------- 卖出：不在 TopK 的清仓；在 TopK 但超配的减仓（并模拟成交更新仓位）----------
        for code in list(current_temp.get_stock_list()):
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
            cur_val = self._position_value(code, sell_amt, trade_start_time, trade_end_time)
            if code not in target_value:
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
                continue

            tgt = target_value[code]
            if cur_val <= tgt + min_rb:
                continue
            p = self._deal_price(code, trade_start_time, trade_end_time)
            if p is None:
                continue
            sell_value = cur_val - tgt
            if sell_value < min_rb:
                continue
            sell_shares = sell_value / p
            sell_shares = min(sell_shares, sell_amt)
            factor = self.trade_exchange.get_factor(
                stock_id=code, start_time=trade_start_time, end_time=trade_end_time
            )
            sell_shares = self.trade_exchange.round_amount_by_trade_unit(
                sell_shares, factor
            )
            if sell_shares <= 0:
                continue
            order = Order(
                stock_id=code,
                amount=sell_shares,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=Order.SELL,
            )
            if self.trade_exchange.check_order(order):
                sell_orders.append(order)
                _, _, _ = self.trade_exchange.deal_order(
                    order, position=current_temp
                )

        # ---------- 买入：按目标加权市值补足低配；现金不足时等比例压缩需求 ----------
        cash_avail = float(current_temp.get_cash())
        buy_needs: dict[str, float] = {}
        for code in buy_codes:
            if not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=None if self.forbid_all_trade_at_limit else OrderDir.BUY,
            ):
                continue
            tgt = target_value[code]
            held = float(current_temp.get_stock_amount(code=code))
            cur_val = self._position_value(code, held, trade_start_time, trade_end_time)
            need = tgt - cur_val
            if need >= min_rb:
                buy_needs[code] = need

        pos_need = sum(buy_needs.values())
        scale = 1.0 if pos_need <= 1e-12 else min(1.0, cash_avail / pos_need)

        buy_orders: list[Order] = []
        for code, need in buy_needs.items():
            adj_need = need * scale
            if adj_need < min_rb:
                continue
            p = self._deal_price(code, trade_start_time, trade_end_time)
            if p is None:
                continue
            buy_amount = adj_need / p
            factor = self.trade_exchange.get_factor(
                stock_id=code, start_time=trade_start_time, end_time=trade_end_time
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

        return TradeDecisionWO(sell_orders + buy_orders, self)
