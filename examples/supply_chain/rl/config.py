# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

env_conf = {
    "scenario": "supply_chain",
    "topology": "SCI",
    "durations": 60,  # number of ticks per episode
}

distribution_features = ("pending_product_quantity", "pending_order_number")
IDX_DISTRIBUTION_PENDING_PRODUCT_QUANTITY, IDX_DISTRIBUTION_PENDING_ORDER_NUMBER = 0, 1

seller_features = ("total_demand", "sold", "demand")
IDX_SELLER_TOTAL_DEMAND, IDX_SELLER_SOLD, IDX_SELLER_DEMAND = 0, 1, 2

NUM_CONSUMER_ACTIONS = 10
ALGO="EOQ"
TEAM_REWARD = True

if ALGO == "PPO":
    OR_NUM_CONSUMER_ACTIONS = 3
else:
    OR_NUM_CONSUMER_ACTIONS = 10

OR_MANUFACTURE_ACTIONS = 20


workflow_settings: dict = {
    "consumption_hist_len": 4,
    "sale_hist_len": 4,
    "pending_order_len": 4,
    # "constraint_state_hist_len": 8,
    "reward_normalization": 1e7,
    "default_vehicle_type": "train",
}
