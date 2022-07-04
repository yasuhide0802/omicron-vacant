# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from collections import defaultdict
from typing import Dict, List

import cvxpy as cp
import numpy as np
import pandas as pd

from maro.rl.policy import RuleBasedPolicy

from ..forecastor.moving_average_forecastor import MovingAverageForecastor
from ..forecastor.oracle_forecastor import OracleForecastor


class BaseStockPolicy(RuleBasedPolicy):
    def __init__(self, name: str, policy_parameters: dict) -> None:
        # Base stock policy action will be determined by quantity.
        super().__init__(name, False)

        forecastor_class = eval(policy_parameters["forecastor"])
        assert issubclass(forecastor_class, (OracleForecastor, MovingAverageForecastor))
        self.forecastor = forecastor_class(policy_parameters)

        self.share_same_stock_level = policy_parameters.get("share_same_stock_level", True)
        self.update_frequency = policy_parameters["update_frequency"]
        self.history_len = policy_parameters["history_len"]
        self.future_len = policy_parameters["future_len"]

        # Use tuple(facility_name, sku_name) as index
        self.product_level_snapshot: Dict[tuple(str, str), Dict[int, int]] = defaultdict(dict)
        self.in_transit_snapshot: Dict[tuple(str, str), Dict[int, int]] = defaultdict(dict)
        self.stock_quantity: Dict[tuple(str, str), Dict[int, int]] = defaultdict(dict)

    def load_data(self, state: dict, history_start: int) -> pd.DataFrame:
        cost = state["upstream_price_mean"]
        # Load history and today data from env
        target_df = pd.DataFrame(columns=["Price", "Cost", "Demand"])
        for index in range(history_start, state["tick"] + 1):
            target_df = target_df.append(
                pd.Series(
                    {
                        "Price": state["history_price"][index],
                        "Cost": cost,
                        "Demand": state["history_demand"][index],
                    },
                ),
                ignore_index=True,
            )

        # Forecast future data by forecastor
        future_demands = self.forecastor.forecast_future_demand(state, target_df)
        his_price_mean = target_df["Price"].mean().item()
        for demand in future_demands:
            target_df = target_df.append(
                pd.Series(
                    {
                        "Price": his_price_mean,
                        "Cost": cost,
                        "Demand": demand,
                    },
                ),
                ignore_index=True,
            )
        return target_df

    def calculate_stock_quantity(
        self,
        input_df: pd.DataFrame,
        product_level: int,
        in_transition_quantity: int,
        vlt: int,
        storage_cost: float,
        purchased_before_action: List[int],
    ) -> np.ndarray:
        # time_hrz_len = history_len + 1 + future_len
        vlt = vlt - 1
        time_hrz_len = len(input_df)
        price = np.round(input_df["Price"], 1)
        order_cost = np.round(input_df["Cost"], 1)
        demand = np.round(input_df["Demand"], 1)

        # Inventory on hand.
        stocks = cp.Variable(time_hrz_len + 1, integer=True)
        # Inventory on the pipeline.
        transits = cp.Variable(time_hrz_len + 1, integer=True)
        sales = cp.Variable(time_hrz_len, integer=True)
        buy = cp.Variable(time_hrz_len + vlt, integer=True)
        # Requested product quantity from upstream.
        buy_in = cp.Variable(time_hrz_len, integer=True)
        # Expected accepted product quantity.
        buy_arv = cp.Variable(time_hrz_len, integer=True)
        target_stock = cp.Variable(time_hrz_len, integer=True)

        profit = cp.Variable(1)

        # Add constraints.
        constraints = [
            # Variable lower bound.
            stocks >= 0,
            transits >= 0,
            sales >= 0,
            buy >= 0,
            # Initial values.
            stocks[0] == product_level,
            transits[0] == in_transition_quantity,
            # Recursion formulas.
            stocks[1 : time_hrz_len + 1] == stocks[0:time_hrz_len] + buy_arv - sales,
            transits[1 : time_hrz_len + 1] == transits[0:time_hrz_len] - buy_arv + buy_in,
            sales <= stocks[0:time_hrz_len] + buy_arv,
            sales <= demand,
            buy_in == buy[vlt : time_hrz_len + vlt],
            buy_arv == buy[0:time_hrz_len],
            target_stock == stocks[0:time_hrz_len] + transits[0:time_hrz_len] + buy_in,
            # Objective function.
            profit
            == cp.sum(
                cp.multiply(price, sales) - cp.multiply(order_cost, buy_in) - cp.multiply(storage_cost, stocks[1:]),
            ),
        ]
        # Init the buy before action
        for i in range(vlt + 1):
            constraints.append(buy[i] == purchased_before_action[i])
        obj = cp.Maximize(profit)
        prob = cp.Problem(obj, constraints)
        prob.solve(solver=cp.GLPK_MI, verbose=True)
        return target_stock.value

    def _get_action_quantity(self, state: dict) -> int:
        index = (state["sku_name"], state["facility_name"])
        current_tick = state["tick"]
        self.product_level_snapshot[index][current_tick + 1] = state["product_level"]
        self.in_transit_snapshot[index][current_tick + 1] = state["in_transition_quantity"]

        if current_tick % self.update_frequency == 0:
            self.history_start = max(current_tick - self.history_len, 0)
            target_df = self.load_data(state, self.history_start)
            purchased_before_action = [0] * state["cur_vlt"]
            for i in range(min(self.history_start, state["cur_vlt"])):
                purchased_before_action[-i - 1] = state["history_purchased"][self.history_start - i - 1]
            self.stock_quantity[index] = self.calculate_stock_quantity(
                target_df,
                self.product_level_snapshot[index].get(self.history_start, 0),
                self.in_transit_snapshot[index].get(self.history_start, 0),
                state["cur_vlt"],
                state["unit_storage_cost"],
                purchased_before_action,
            )
        if self.share_same_stock_level:
            stock_quantity = max(self.stock_quantity[index])
        else:
            if current_tick - self.history_start + 1 < len(self.stock_quantity[index]):
                stock_quantity = self.stock_quantity[index][current_tick - self.history_start + 1]
            else:
                stock_quantity = 0

        booked_quantity = state["product_level"] + state["in_transition_quantity"] - state["to_distribute_quantity"]
        quantity = stock_quantity - booked_quantity
        return quantity

    def _rule(self, states: List[dict]) -> List[int]:
        return [self._get_action_quantity(state) for state in states]
