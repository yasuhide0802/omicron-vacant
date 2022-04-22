# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.


from typing import Dict, List, Optional

import numpy as np
import scipy.stats as st
from examples.supply_chain.rl.config import IDX_CONSUMER_ORDER_COST

from maro.simulator.scenarios.supply_chain.facilities import FacilityBase, FacilityInfo
from maro.simulator.scenarios.supply_chain.objects import SupplyChainEntity


class ScOrAgentStates:
    def __init__(
        self,
        entity_dict: Dict[int, SupplyChainEntity],
        facility_info_dict: Dict[int, FacilityInfo],
        global_sku_id2idx: Dict[int, int],
    ) -> None:
        self._entity_dict: Dict[int, SupplyChainEntity] = entity_dict
        self._facility_info_dict: Dict[int, FacilityInfo] = facility_info_dict
        self._global_sku_id2idx: Dict[int, int] = global_sku_id2idx

        self._storage_unit_cost_dict: Optional[Dict[int, Dict[int, int]]] = None
        self._storage_capacity_dict: Optional[Dict[int, Dict[int, int]]] = None

        self._templates: Dict[int, dict] = {}

    def _init_entity_state(self, entity: SupplyChainEntity) -> dict:
        facility_info = self._facility_info_dict[entity.facility_id]
        storage_index = facility_info.storage_info.node_index

        state: dict = {
            "sale_mean": 0,
            "sale_std": 0,
            "unit_storage_cost": self._storage_unit_cost_dict[storage_index][entity.skus.id],
            "order_cost": 1,
            "storage_capacity": self._storage_capacity_dict[storage_index][entity.skus.id],
            "storage_utilization": 0,
            "storage_in_transition_quantity": 0,
            "product_level": 0,
            "in_transition_quantity": 0,
            "max_vlt": facility_info.products_info[entity.skus.id].max_vlt,
            "service_level_ppf": st.norm.ppf(entity.skus.service_level),
        }

        return state

    def _update_entity_state(
        self,
        entity_id: int,
        storage_unit_cost_dict: Optional[Dict[int, Dict[int, int]]],
        storage_capacity_dict: Optional[Dict[int, Dict[int, int]]],
        product_metrics: Optional[dict],
        cur_consumer_hist_states: np.ndarray,
        product_levels: List[int],
        in_transit_order_quantity: List[int],
    ) -> dict:
        entity: SupplyChainEntity = self._entity_dict[entity_id]

        if issubclass(entity.class_type, FacilityBase):
            return {}

        if entity_id not in self._templates:
            if self._storage_unit_cost_dict is None:
                self._storage_unit_cost_dict = storage_unit_cost_dict
                self._storage_capacity_dict = storage_capacity_dict

            self._templates[entity_id] = self._init_entity_state(entity)

        state: dict = self._templates[entity_id]

        facility_info: FacilityInfo = self._facility_info_dict[entity.facility_id]
        consumer_info = facility_info.products_info[entity.skus.id].consumer_info

        state["sale_mean"] = product_metrics["sale_mean"]
        state["sale_std"] = product_metrics["sale_std"]

        state["order_cost"] = cur_consumer_hist_states[-1, consumer_info.node_index, IDX_CONSUMER_ORDER_COST]

        state["storage_utilization"] = sum(product_levels)
        state["storage_in_transition_quantity"] = sum(in_transit_order_quantity)

        state["product_level"] = product_levels[self._global_sku_id2idx[entity.skus.id]]
        state["in_transition_quantity"] = in_transit_order_quantity[self._global_sku_id2idx[entity.skus.id]]

        return state