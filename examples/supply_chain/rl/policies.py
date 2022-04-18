# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from functools import partial
from typing import Any, Dict

from maro.simulator import Env
from maro.simulator.scenarios.supply_chain import ConsumerUnit, ManufactureUnit, ProductUnit, SellerUnit
from maro.simulator.scenarios.supply_chain.business_engine import SupplyChainBusinessEngine
from maro.simulator.scenarios.supply_chain.facilities import FacilityInfo
from maro.simulator.scenarios.supply_chain.objects import SupplyChainEntity

from .agent_state import STATE_DIM
from .algorithms.ppo import get_policy, get_ppo
from .algorithms.rule_based import DummyPolicy, ManufacturerBaselinePolicy
from .config import NUM_CONSUMER_ACTIONS, env_conf


# Create an env to get entity list and env summary
env = Env(**env_conf)

facility_info_dict: Dict[int, FacilityInfo] = env.summary["node_mapping"]["facilities"]

helper_business_engine = env.business_engine
assert isinstance(helper_business_engine, SupplyChainBusinessEngine)

entity_dict: Dict[Any, SupplyChainEntity] = {
    entity.id: entity
    for entity in helper_business_engine.get_entity_list()
}


def entity2policy(entity: SupplyChainEntity) -> str:
    if entity.skus is None:
        return "facility_policy"
    elif issubclass(entity.class_type, ManufactureUnit):
        return "manufacturer_policy"
    elif issubclass(entity.class_type, ProductUnit):
        return "product_policy"
    elif issubclass(entity.class_type, SellerUnit):
        return "seller_policy"
    elif issubclass(entity.class_type, ConsumerUnit):
        facility_name = facility_info_dict[entity.facility_id].name
        if "Plant" in facility_name:
            # Return the policy name if needed
            pass
        elif "Warehouse" in facility_name:
            # Return the policy name if needed
            pass
        elif "Store" in facility_name:
            # Return the policy name if needed
            pass
        return "ppo.policy"
    raise TypeError(f"Unrecognized entity class type: {entity.class_type}")


policy_creator = {
    "ppo.policy": partial(get_policy, STATE_DIM, NUM_CONSUMER_ACTIONS),
    "manufacturer_policy": lambda name: ManufacturerBaselinePolicy(name),
    "facility_policy": lambda name: DummyPolicy(name),
    "product_policy": lambda name: DummyPolicy(name),
    "seller_policy": lambda name: DummyPolicy(name),
}

agent2policy = {
    id_: entity2policy(entity) for id_, entity in entity_dict.items()
}

trainable_policies = ["ppo.policy"]

trainer_creator = {
    "ppo": partial(get_ppo, STATE_DIM),
}