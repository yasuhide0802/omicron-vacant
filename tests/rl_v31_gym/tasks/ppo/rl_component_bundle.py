import numpy as np
import torch
from gym import spaces
from torch import nn
from torch.distributions import Normal
from torch.optim import Adam, RMSprop

from maro.rl.model import FullyConnected
from maro.rl_v31.model.base import BaseNet, PolicyModel
from maro.rl_v31.model.vnet import VCritic
from maro.rl_v31.policy import PPOPolicy
from maro.rl_v31.rl_component_bundle.rl_component_bundle import RLComponentBundle
from maro.rl_v31.training.algorithms.ppo import PPOTrainer
from maro.rl_v31.training.replay_memory import ReplayMemory, ReplayMemoryManager
from maro.simulator import Env
from tests.rl_v31_gym.gym_wrapper.common import (action_lower_bound, action_upper_bound, env, env_conf, gym_action_dim,
                                                 gym_state_dim, num_agents)
from tests.rl_v31_gym.gym_wrapper.env_wrapper import GymEnvWrapper
from tests.rl_v31_gym.gym_wrapper.simulator.business_engine import GymBusinessEngine

actor_net_conf = {
    "hidden_dims": [64, 32],
    "activation": torch.nn.Tanh,
}
critic_net_conf = {
    "hidden_dims": [64, 32],
    "activation": torch.nn.Tanh,
}
actor_learning_rate = 3e-4
critic_learning_rate = 1e-3


class MyPolicyModel(PolicyModel):
    def __init__(self, obs_dim: int, action_dim: int) -> None:
        super().__init__()

        log_std = -0.5 * np.ones(action_dim, dtype=np.float32)
        self._log_std = torch.nn.Parameter(torch.as_tensor(log_std))
        self._mu_net = FullyConnected(
            input_dim=obs_dim,
            hidden_dims=actor_net_conf["hidden_dims"],
            output_dim=action_dim,
            activation=actor_net_conf["activation"],
        )

    def distribution(self, obs: torch.Tensor) -> Normal:
        mu = self._mu_net(obs.float())
        std = torch.exp(self._log_std)
        return Normal(mu, std)

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        dist = self.distribution(obs)
        actions = dist.sample()
        return actions


class MyCriticModel(BaseNet):
    def __init__(self, obs_dim: int) -> None:
        super().__init__()

        self.mlp = FullyConnected(
            input_dim=obs_dim,
            output_dim=1,
            hidden_dims=critic_net_conf["hidden_dims"],
            activation=critic_net_conf["activation"],
        )

    def forward(self, obs: torch.Tensor) -> torch.Tensor:
        return self.mlp(obs).squeeze(-1)


def get_ppo_policy(name: str, lower_bound: float, upper_bound: float, obs_dim: int, action_dim: int) -> PPOPolicy:
    obs_space = spaces.Box(lower_bound, upper_bound, shape=(obs_dim,))
    action_space = spaces.Box(lower_bound, upper_bound, shape=(action_dim,))
    model = MyPolicyModel(obs_dim=obs_dim, action_dim=action_dim)
    optim = Adam(model.parameters(), lr=actor_learning_rate)

    return PPOPolicy(
        name=name,
        obs_space=obs_space,
        action_space=action_space,
        model=model,
        optim=optim,
        is_discrete=False,
        dist_fn=model.distribution,
    )


def get_ppo_critic(obs_dim: int) -> VCritic:
    model = MyCriticModel(obs_dim=obs_dim)
    optim = RMSprop(model.parameters(), lr=critic_learning_rate)

    return VCritic(model=model, optim=optim)


agent2policy = {agent: f"ppo_{agent}.policy" for agent in env.agent_idx_list}
policies = [
    get_ppo_policy(f"ppo_{i}.policy", action_lower_bound, action_upper_bound, gym_state_dim, gym_action_dim)
    for i in range(num_agents)
]
trainers = [
    PPOTrainer(
        name=f'ppo_{i}',
        # TODO: create rmm in collector?
        rmm=ReplayMemoryManager(memories=[ReplayMemory(capacity=1000) for _ in range(1)]),  # TODO: config parallelism & memory size
        critic_func=lambda: get_ppo_critic(gym_state_dim),
        critic_loss_cls=nn.SmoothL1Loss,
        lam=0.97,
        reward_discount=0.99,
        clip_ratio=0.1,
        grad_iters=80,
    )
    for i in range(num_agents)
]

breakpoint()

rl_component_bundle = RLComponentBundle(
    env_wrapper_func=lambda: GymEnvWrapper(Env(business_engine_cls=GymBusinessEngine, **env_conf)),
    agent2policy=agent2policy,
    policies=policies,
    trainers=trainers,
    metrics_agg_func=None,  # TODO
)