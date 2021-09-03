# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from collections import defaultdict
from typing import List, Tuple

import numpy as np
import torch

from maro.rl.modeling import DiscretePolicyNet
from maro.rl.utils import discount_cumsum

from .policy import RLPolicy


class PolicyGradient(RLPolicy):
    class Buffer:
        """Sequence of transitions for an agent.

        Args:
            states: Sequence of ``State`` objects traversed during simulation.
            actions: Sequence of actions taken in response to the states.
            rewards: Sequence of rewards received as a result of the actions.
            info: Sequence of each transition's auxillary information.
        """
        def __init__(self, state_dim, size: int = 10000):
            self.states = np.zeros((size, state_dim), dtype=np.float32)
            self.values = np.zeros(size, dtype=np.float32)
            self.rewards = np.zeros(size, dtype=np.float32)
            self.terminals = np.zeros(size, dtype=np.bool)
            self.size = size

        def put(self, state: np.ndarray, action: dict, reward: float, terminal: bool = False):
            self.states[self._ptr] = state
            self.values[self._ptr] = action["value"]
            self.rewards[self._ptr] = reward
            self.terminals[self._ptr] = terminal
            # increment pointer
            self._ptr += 1
            if self._ptr == self.size:
                self._ptr = 0

        def get(self):
            terminal = self.terminals[self._ptr - 1]
            traj_slice = slice(self._last_ptr, self._ptr - (not terminal))
            self._last_ptr = self._ptr - (not terminal)
            return {
                "states": self.states[traj_slice],
                "rewards": self.rewards[traj_slice],
                "last_value": self.values[-1]
            }

    """The vanilla Policy Gradient (VPG) algorithm, a.k.a., REINFORCE.

    Reference: https://github.com/openai/spinningup/tree/master/spinup/algos/pytorch.

    Args:
        name (str): Unique identifier for the policy.
        policy_net (DiscretePolicyNet): Multi-task model that computes action distributions and state values.
            It may or may not have a shared bottom stack.
        reward_discount (float): Reward decay as defined in standard RL terminology.
        grad_iters (int): Number of gradient steps for each batch or set of batches. Defaults to 1.
    """
    def __init__(
        self,
        name: str,
        policy_net: DiscretePolicyNet,
        reward_discount: float,
        grad_iters: int = 1,
        buffer_size: int = 10000,
        get_loss_on_rollout: bool = False
    ):
        if not isinstance(policy_net, DiscretePolicyNet):
            raise TypeError("model must be an instance of 'DiscretePolicyNet'")
        super().__init__(name)
        self.policy_net = policy_net
        self.device = self.policy_net.device
        self.reward_discount = reward_discount
        self.grad_iters = grad_iters
        self.buffer_size = buffer_size
        self.get_loss_on_rollout = get_loss_on_rollout

        self._buffer = defaultdict(lambda: self.Buffer(self.policy_net.input_dim, size=self.buffer_size))

    def choose_action(self, states: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Return actions and log probabilities for given states."""
        self.policy_net.eval()
        with torch.no_grad():
            actions, log_p = self.policy_net.get_action(states)
        actions, log_p = actions.cpu().numpy(), log_p.cpu().numpy()
        return (actions[0], log_p[0]) if len(actions) == 1 else actions, log_p

    def record(
        self,
        key: str,
        state: np.ndarray,
        action: dict,
        reward: float,
        next_state: np.ndarray,
        terminal: bool
    ):
        self._buffer[key].put(state, action, reward, terminal)

    def get_rollout_info(self):
        if self._get_loss_on_rollout_finish:
            return self.get_batch_loss(self._get_batch(), explicit_grad=True)
        else:
            return self._get_batch()

    def _get_batch(self):
        batch = defaultdict(list)
        for buf in self._buffer:
            trajectory = buf.get()
            rewards = np.append(trajectory["rewards"], trajectory["last_val"])
            batch["states"].append(trajectory["states"])
            # Returns rewards-to-go, to be targets for the value function
            batch["returns"].append(discount_cumsum(rewards, self.reward_discount)[:-1])

        return {key: np.concatenate(vals) for key, vals in batch.items}

    def get_batch_loss(self, batch: dict, explicit_grad: bool = False):
        """
        This should be called at the end of a simulation episode and the experiences obtained from
        the experience store's ``get`` method should be a sequential set, i.e., in the order in
        which they are generated during the simulation. Otherwise, the return values may be meaningless.
        """
        assert self.policy_net.trainable, "policy_net needs to have at least one optimizer registered."
        self.policy_net.train()

        returns = torch.from_numpy(np.asarray(batch.returns)).to(self.device)

        _, logp = self.policy_net(batch["states"])
        loss = -(logp * returns).mean()
        loss_info = {"loss": loss.detach().cpu().numpy()}
        if explicit_grad:
            loss_info["grad"] = self.policy_net.get_gradients(loss)
        return loss_info

    def update(self, loss_info_list: List[dict]):
        """Apply gradients to the underlying parameterized model."""
        self.policy_net.apply_gradients([loss_info["grad"] for loss_info in loss_info_list])

    def learn(self, batch: dict):
        for _ in range(self.grad_iters):
            self.policy_net.step(self.get_batch_loss(batch)["grad"])

    def set_state(self, policy_state):
        self.policy_net.load_state_dict(policy_state)

    def get_state(self):
        return self.policy_net.state_dict()