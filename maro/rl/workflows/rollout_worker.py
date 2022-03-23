# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from functools import partial

from maro.rl.rollout import RolloutWorker
from maro.rl.utils.common import get_env, int_or_none
from maro.rl.workflows.scenario import Scenario
from maro.utils import LoggerV2

if __name__ == "__main__":
    scenario = Scenario(get_env("SCENARIO_PATH"))
    policy_creator = scenario.policy_creator
    agent2policy = scenario.agent2policy
    trainable_policies = scenario.trainable_policies

    worker_idx = int_or_none(get_env("ID"))
    logger = LoggerV2(
        f"ROLLOUT-WORKER.{worker_idx}",
        dump_path=get_env("LOG_PATH"),
        dump_mode="a",
        stdout_level=get_env("LOG_LEVEL_STDOUT", required=False, default="CRITICAL"),
        file_level=get_env("LOG_LEVEL_FILE", required=False, default="CRITICAL"),
    )
    worker = RolloutWorker(
        idx=worker_idx,
        env_sampler_creator=partial(scenario.env_sampler_creator, policy_creator, agent2policy, trainable_policies),
        producer_host=get_env("ROLLOUT_CONTROLLER_HOST"),
        producer_port=int_or_none(get_env("ROLLOUT_CONTROLLER_PORT")),
        logger=logger,
    )
    worker.start()
