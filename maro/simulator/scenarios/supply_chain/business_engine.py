# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.


import os
from typing import List, Tuple

from maro.event_buffer import MaroEvents
from maro.simulator.scenarios import AbsBusinessEngine

from .parser import ConfigParser, SupplyChainConfiguration
from .units import ProductUnit, UnitBase
from .world import World


class SupplyChainBusinessEngine(AbsBusinessEngine):
    def __init__(self, **kwargs):
        super().__init__(scenario_name="supply_chain", **kwargs)

        self._register_events()

        self._build_world()

        self._product_units = []

        # Prepare product unit for later using.
        for unit in self.world.units.values():
            if issubclass(type(unit), ProductUnit):
                self._product_units.append(unit)

        self._frame = self.world.frame

        self._node_mapping = self.world.get_node_mapping()

        # Used to cache the action from outside, then dispatch to units at the beginning of step.
        self._action_cache = None

        self._metrics_cache = None

    @property
    def frame(self):
        return self._frame

    @property
    def snapshots(self):
        return self._frame.snapshots

    @property
    def configs(self) -> SupplyChainConfiguration:
        return self.world.configs

    def step(self, tick: int):
        # Clear the metrics cache.
        self._metrics_cache = None

        # NOTE: we have to dispatch the action here.
        self._dispatch_action()
        self._step_by_facility(tick)

        # We do not have payload here.
        decision_event = self._event_buffer.gen_decision_event(tick, None)

        self._event_buffer.insert_event(decision_event)

    def post_step(self, tick: int):
        self._post_step_by_facility(tick)

        return tick + 1 == self._max_tick

    def reset(self):
        self._frame.reset()

        if self._frame.snapshots:
            self._frame.snapshots.reset()

        self._reset_by_facility()

        self._action_cache = None

    def get_node_mapping(self) -> dict:
        return self._node_mapping

    def get_agent_idx_list(self) -> List[Tuple[str, int]]:
        """Get a list of agent index.

        Returns:
            list: List of agent index.
        """
        return self.world.agent_list

    def _step_by_facility(self, tick: int):
        """Call step functions by facility.

        Args:
            tick (int): Current tick.
        """
        # Step first.
        for facility in self.world.facilities.values():
            facility.step(tick)

        # Then flush states to frame before generate decision event.
        for facility in self.world.facilities.values():
            facility.flush_states()

    def _post_step_by_facility(self, tick: int):
        """Call post_step functions by facility."""
        for facility in self.world.facilities.values():
            facility.post_step(tick)

    def _reset_by_facility(self):
        """Call reset functions by facility."""
        for facility in self.world.facilities.values():
            facility.reset()

    def _register_events(self):
        self._event_buffer.register_event_handler(
            MaroEvents.TAKE_ACTION, self._on_action_received)

    def _build_world(self):
        self.update_config_root_path(__file__)

        # Core configuration always in topologies folder.
        be_root = os.path.split(os.path.realpath(__file__))[0]
        core_config = os.path.join(be_root, "topologies", "core.yml")

        config_path = os.path.join(self._config_path, "config.yml")

        parser = ConfigParser(core_config, config_path)

        conf = parser.parse()

        self.world = World()

        self.world.build(conf, self.calc_max_snapshots(), self._max_tick)

    def _on_action_received(self, event):
        action = event.payload

        if action is not None and type(action) == dict and len(action) > 0:
            self._action_cache = action

    def _dispatch_action(self):
        if self._action_cache is not None:
            # NOTE: we assume that the action is dictionary that key is the unit(agent) id, value is the real action.
            for unit_id, action_obj in self._action_cache.items():
                entity = self.world.get_entity(unit_id)

                if entity is not None and issubclass(type(entity), UnitBase):
                    entity.set_action(action_obj)

            self._action_cache = None

    def get_metrics(self):
        if self._metrics_cache is None:
            self._metrics_cache = {
                "products": {
                    product.id: {
                        "sale_mean": product.get_sale_mean(),
                        "sale_std": product.get_sale_std(),
                        "selling_price": product.get_selling_price(),
                        "pending_order_daily":
                            None if product.consumer is None else product.consumer.pending_order_daily
                    } for product in self._product_units
                },
                "facilities": {
                    facility.id: {
                        "in_transit_orders": facility.get_in_transit_orders(),
                        "pending_order":
                            None if facility.distribution is None else facility.distribution.get_pending_order()
                    } for facility in self.world.facilities.values()
                }
            }

        return self._metrics_cache