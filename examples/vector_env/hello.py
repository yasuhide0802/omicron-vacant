# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from enum import Enum
from maro.simulator.scenarios.cim.common import Action, ActionType, DecisionEvent
from maro.vector_env import VectorEnv

class VectorEnvUsage(Enum):
    PUSH_ONE_FORWARD = "push_one_forward_and_others_behind"
    PUSH_ALL_FORWARD = "push_all_forward"

USAGE = VectorEnvUsage.PUSH_ALL_FORWARD

if __name__ == "__main__":
    with VectorEnv(batch_num=4, scenario="cim", topology="toy.5p_ssddd_l0.0", durations=100) as env:
        for ep in range(2):
            print("current episode:", ep)

            metrics, decision_event, is_done = (None, None, False)

            while not is_done:
                action = None

                if decision_event:
                    env0_dec: DecisionEvent = decision_event[0]

                    # Showcase: how to access information from snapshot list in vector env.
                    if env0_dec:
                        ss0 = env.snapshot_list["vessels"][env0_dec.tick:env0_dec.vessel_idx:"remaining_space"]

                    # 1. Only push specified (1st for this example) environment, leave others behind.
                    if USAGE == VectorEnvUsage.PUSH_ONE_FORWARD and env0_dec:
                        # Only action for the 1st Env. After 1st environment is done, then others will push forward.
                        action = {
                            0: Action(
                                vessel_idx=env0_dec.vessel_idx,
                                port_idx=env0_dec.port_idx,
                                quantity=env0_dec.action_scope.load,
                                action_type=ActionType.LOAD
                            )
                        }

                    # 2. Only pass action to 1st environment (give None to other environments),
                    # but keep pushing all the environment, until the end
                    elif USAGE == VectorEnvUsage.PUSH_ALL_FORWARD and env0_dec:
                        # With a list of action, will push all environment to next step.
                        action = [None] * env.batch_number
                        action[0] = Action(
                            vessel_idx=env0_dec.vessel_idx,
                            port_idx=env0_dec.port_idx,
                            quantity=env0_dec.action_scope.load,
                            action_type=ActionType.LOAD
                        )

                metrics, decision_event, is_done = env.step(action)

            print("Final tick for each environment:", env.tick)
            print("Final frame index for each environment:", env.frame_index)

            env.reset()
