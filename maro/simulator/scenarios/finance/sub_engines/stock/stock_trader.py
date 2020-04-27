from collections import OrderedDict
from maro.simulator.scenarios.finance.sub_engines.common.trader import Trader
from maro.simulator.scenarios.finance.common import (OrderMode)
from maro.simulator.scenarios.finance.sub_engines.common.order import MarketOrder, LimitOrder, StopOrder, StopLimitOrder
from maro.simulator.scenarios.finance.sub_engines.common.slippage import ByMoneySlippage
from maro.simulator.scenarios.finance.sub_engines.common.commission import ByMoneyCommission, StampTaxCommission

# decision_event = DecisionEvent(tick, FinanceType.stock, valid_stocks, self.name, self._action_scope)


class StockTrader(Trader):

    def __init__(self, trade_constrain: OrderedDict):
        Trader.__init__(self, trade_constrain)

        self.order_handler_register(OrderMode.market_order, MarketOrder())
        self.order_handler_register(OrderMode.limit_order, LimitOrder())
        self.order_handler_register(OrderMode.stop_order, StopOrder())
        self.order_handler_register(OrderMode.stop_limit_order, StopLimitOrder())

        self.slippage_handler_register(ByMoneySlippage(0.00246))
        self.commission_handler_register(ByMoneyCommission(0.0003, 5))
        self.commission_handler_register(StampTaxCommission(0.001))
