# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from abc import ABC
from collections import defaultdict
from typing import Dict, List

from maro.simulator.scenarios.supply_chain.easy_config import SkuInfo
from maro.simulator.scenarios.supply_chain.units import DistributionUnit, ProductUnit, StorageUnit


class FacilityBase(ABC):
    """Base of all facilities."""

    # Id of this facility.
    id: int = None

    # Name of this facility.
    name: str = None

    # World of this facility belongs to.
    world = None

    # Skus in this facility.
    skus: Dict[int, SkuInfo] = None

    # Product units for each sku in this facility.
    # Key is sku(product) id, value is the instance of product unit.
    products: Dict[int, ProductUnit] = None

    # Storage unit in this facility.
    storage: StorageUnit = None

    # Distribution unit in this facility.
    distribution: DistributionUnit = None

    # Upstream facilities.
    # Key is sku id, value is the list of product unit from upstream.
    upstreams: Dict[int, List[ProductUnit]] = None

    # Down stream facilities, value same as upstreams.
    downstreams: Dict[int, List[ProductUnit]] = None

    # Configuration of this facility.
    configs: dict = None

    # Name of data model, from configuration.
    data_model_name: str = None

    # Index of the data model node.
    data_model_index: int = 0

    data_model: object = None

    # Children of this facility (valid units).
    children: list = None

    def __init__(self):
        self.upstreams = {}
        self.downstreams = {}
        self.children = []
        self.skus = {}

    def parse_skus(self, configs: dict):
        """Parse sku information from config.

        Args:
            configs (dict): Configuration of skus belongs to this facility.
        """
        for sku_name, sku_config in configs.items():
            global_sku = self.world.get_sku_by_name(sku_name)
            facility_sku = SkuInfo(sku_config)
            facility_sku.id = global_sku.id

            self.skus[global_sku.id] = facility_sku

    def parse_configs(self, configs: dict):
        """Parse configuration of this facility.

        Args:
            configs (dict): Configuration of this facility.
        """
        self.configs = configs

    def get_config(self, key: str, default: object = None) -> object:
        """Get specified configuration of facility.

        Args:
            key (str): Key of the configuration.
            default (object): Default value if key not exist, default is None.

        Returns:
            object: value in configuration.
        """
        return default if self.configs is None else self.configs.get(key, default)

    def initialize(self):
        """Initialize this facility after frame is ready."""
        self.data_model.initialize()
        self.data_model.set_id(self.id, 0, 0)
        self.data_model.reset()

        # Put valid units into the children, used to simplify following usage.
        if self.storage is not None:
            self.children.append(self.storage)

        if self.distribution is not None:
            self.children.append(self.distribution)

        if self.products is not None:
            for product in self.products.values():
                self.children.append(product)

    def step(self, tick: int):
        """Push facility to next step.

        Args:
            tick (int): Current simulator tick.
        """
        for unit in self.children:
            unit.step(tick)

    def flush_states(self):
        """Flush states into frame."""
        for unit in self.children:
            unit.flush_states()

    def post_step(self, tick: int):
        """Post processing at the end of step."""
        for unit in self.children:
            unit.post_step(tick)

    def reset(self):
        """Reset facility for new episode."""
        for unit in self.children:
            unit.reset()

        if self.data_model is not None:
            self.data_model.reset()

    def get_in_transit_orders(self):
        in_transit_orders = defaultdict(int)

        for product_id, product in self.products.items():
            if product.consumer is not None:
                in_transit_orders[product_id] = product.consumer.get_in_transit_quantity()

        return in_transit_orders

    def set_action(self, action: object):
        pass

    def get_node_info(self) -> dict:
        products_info = {}

        for product_id, product in self.products.items():
            products_info[product_id] = product.get_unit_info()

        return {
            "id": self.id,
            "name": self.name,
            "class": type(self),
            "node_index": self.data_model_index,
            "units": {
                "storage": self.storage.get_unit_info() if self.storage is not None else None,
                "distribution": self.distribution.get_unit_info() if self.distribution is not None else None,
                "products": products_info
            },
            "configs": self.configs,
            "skus": self.skus,
            "upstreams": {
                product_id: [f.id for f in source_list]
                for product_id, source_list in self.upstreams.items()
            },
            "downstreams": {
                product_id: [f.id for f in source_list]
                for product_id, source_list in self.downstreams.items()
            }
        }