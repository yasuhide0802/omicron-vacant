# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from maro.rl_v31.policy.dqn import DQNPolicy
from maro.rl_v31.policy.pg import ContinuousPGPolicy, PGPolicy

DDPGPolicy = ContinuousPGPolicy
ActorCriticPolicy = PGPolicy
PPOPolicy = PGPolicy
MADDPGPolicy = PGPolicy

__all__ = [
    "ActorCriticPolicy",
    "DDPGPolicy",
    "DQNPolicy",
    "PPOPolicy",
    "MADDPGPolicy",
]