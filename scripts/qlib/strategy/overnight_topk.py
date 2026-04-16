"""
收盘调仓 TopK：与标签 ``Ref($close,-1)/$close-1``（次日收盘相对当日收盘）一致时，须 ``deal_price=("$close", "$close")``。

每个交易日：
 1. 先 **按收盘价卖出** 全部持仓；
 2. 再 **按收盘价、等权重** 买入当日预测分最高的 ``topk`` 只（分数仅用于排序，不按分数分配仓位）。

回测需在 ``Exchange`` 中设置 ``deal_price=(买入价, 卖出价)=("$close", "$close")``。
信号时间与决策 bar 对齐（当日预测、当日调仓），通过对 ``BaseSignalStrategy`` 的交易日历做补丁实现。
"""

from __future__ import annotations

import copy

import pandas as pd

from qlib.backtest.decision import Order, OrderDir, TradeDecisionWO
from qlib.contrib.strategy.signal_strategy import BaseSignalStrategy


class OvernightTopkStrategy(BaseSignalStrategy):
    """每日尾盘：先清仓再按 TopK 满仓（买卖均按收盘撮合；多头、入选标的等权）。"""

    def __init__(
        self,
        *,
        topk: int = 4,
        only_tradable: bool = True,
        forbid_all_trade_at_limit: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.topk = int(topk)
        self.only_tradable = only_tradable
        self.forbid_all_trade_at_limit = forbid_all_trade_at_limit

    def generate_trade_decision(self, execute_result=None):
        cal = self.trade_calendar
        orig_get_step_time = cal.get_step_time

        def get_step_time_same_day(trade_step=None, shift=0):
            if shift == 1:
                shift = 0
            return orig_get_step_time(trade_step, shift=shift)

        cal.get_step_time = get_step_time_same_day
        try:
            return self._decision(execute_result)
        finally:
            cal.get_step_time = orig_get_step_time

    def _decision(self, execute_result=None):
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

        sell_orders = []
        buy_orders = []
        current_temp = copy.deepcopy(self.trade_position)
        cash = float(current_temp.get_cash())

        for code in list(current_temp.get_stock_list()):
            if not self.trade_exchange.is_stock_tradable(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=None if self.forbid_all_trade_at_limit else OrderDir.SELL,
            ):
                continue
            sell_amt = current_temp.get_stock_amount(code=code)
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
                trade_val, trade_cost, _ = self.trade_exchange.deal_order(
                    order, position=current_temp
                )
                cash += trade_val - trade_cost

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
            return TradeDecisionWO(sell_orders, self)

        deploy = cash * self.get_risk_degree(trade_step)
        value_each = deploy / len(buy_codes)
        for code in buy_codes:
            buy_price = self.trade_exchange.get_deal_price(
                stock_id=code,
                start_time=trade_start_time,
                end_time=trade_end_time,
                direction=OrderDir.BUY,
            )
            if buy_price is None or (
                isinstance(buy_price, float) and buy_price <= 1e-8
            ):
                continue
            buy_amount = value_each / float(buy_price)
            factor = self.trade_exchange.get_factor(
                stock_id=code, start_time=trade_start_time, end_time=trade_end_time
            )
            buy_amount = self.trade_exchange.round_amount_by_trade_unit(
                buy_amount, factor
            )
            buy_orders.append(
                Order(
                    stock_id=code,
                    amount=buy_amount,
                    start_time=trade_start_time,
                    end_time=trade_end_time,
                    direction=Order.BUY,
                )
            )

        return TradeDecisionWO(sell_orders + buy_orders, self)
