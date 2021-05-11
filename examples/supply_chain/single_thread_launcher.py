# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import sys
from os.path import dirname, realpath

from maro.rl import EpisodeBasedSchedule, LocalLearner, MultiPolicyUpdateSchedule, StepBasedSchedule
from maro.simulator import Env

sc_code_dir = dirname(realpath(__file__))
sys.path.insert(0, sc_code_dir)
from config import config
from env_wrapper import SCEnvWrapper
from exploration import exploration_dict, agent2exploration
from policies import agent2policy, policy_dict


# Single-threaded launcher
if __name__ == "__main__":
    env = SCEnvWrapper(Env(**config["env"]))
    policy_update_schedule = MultiPolicyUpdateSchedule(EpisodeBasedSchedule(3, 2))
    # create a learner to start training
    learner = LocalLearner(
        policy_dict, agent2policy, env, config["num_episodes"], policy_update_schedule,
        exploration_dict=exploration_dict,
        agent2exploration=agent2exploration,
        experience_update_interval=config["experience_update_interval"],
        eval_schedule=config["eval_schedule"],
        log_env_metrics=config["log_env_metrics"]
    )
    learner.run()