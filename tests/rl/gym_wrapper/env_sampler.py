# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from typing import Any, Dict, List, Tuple, Type, Union, cast

import numpy as np
from gym import spaces

from maro.rl.policy.abs_policy import AbsPolicy
from maro.rl.rollout import AbsEnvSampler, CacheElement
from maro.rl.rollout.env_sampler import AbsAgentWrapper, SimpleAgentWrapper
from maro.simulator.core import Env

from tests.rl.gym_wrapper.simulator.business_engine import GymBusinessEngine
from tests.rl.gym_wrapper.simulator.common import Action, DecisionEvent


class GymEnvSampler(AbsEnvSampler):
    def __init__(
        self,
        learn_env: Env,
        test_env: Env,
        policies: List[AbsPolicy],
        agent2policy: Dict[Any, str],
        trainable_policies: List[str] = None,
        agent_wrapper_cls: Type[AbsAgentWrapper] = SimpleAgentWrapper,
        reward_eval_delay: int = None,
        max_episode_length: int = None,
    ) -> None:
        super(GymEnvSampler, self).__init__(
            learn_env=learn_env,
            test_env=test_env,
            policies=policies,
            agent2policy=agent2policy,
            trainable_policies=trainable_policies,
            agent_wrapper_cls=agent_wrapper_cls,
            reward_eval_delay=reward_eval_delay,
            max_episode_length=max_episode_length,
        )

        self._sample_rewards = []
        self._eval_rewards = []

        gym_env = cast(GymBusinessEngine, learn_env.business_engine).gym_env
        gym_action_space = gym_env.action_space
        self._is_discrete = isinstance(gym_action_space, spaces.Discrete)

    def _get_global_and_agent_state_impl(
        self,
        event: DecisionEvent,
        tick: int = None,
    ) -> Tuple[Union[None, np.ndarray, list], Dict[Any, Union[np.ndarray, list]]]:
        return None, {0: event.state}

    def _translate_to_env_action(self, action_dict: dict, event: Any) -> dict:
        return {k: Action(v.item() if self._is_discrete else v) for k, v in action_dict.items()}

    def _get_reward(self, env_action_dict: dict, event: Any, tick: int) -> Dict[Any, float]:
        be = self._env.business_engine
        assert isinstance(be, GymBusinessEngine)
        return {0: be.get_reward_at_tick(tick)}

    def _post_step(self, cache_element: CacheElement) -> None:
        if not (self._end_of_episode or self.truncated):
            return
        rewards = list(self._env.metrics["reward_record"].values())
        self._sample_rewards.append((len(rewards), np.sum(rewards)))

    def _post_eval_step(self, cache_element: CacheElement) -> None:
        if not (self._end_of_episode or self.truncated):
            return
        rewards = list(self._env.metrics["reward_record"].values())
        self._eval_rewards.append((len(rewards), np.sum(rewards)))

    def post_collect(self, ep: int) -> None:
        if len(self._sample_rewards) > 0:
            cur = {
                "n_steps": sum([n for n, _ in self._sample_rewards]),
                "n_segment": len(self._sample_rewards),
                "avg_reward": np.mean([r for _, r in self._sample_rewards]),
                "avg_n_steps": np.mean([n for n, _ in self._sample_rewards]),
                "max_n_steps": np.max([n for n, _ in self._sample_rewards]),
                "n_interactions": self._total_number_interactions,
            }
            self.metrics.update(cur)
            # clear validation metrics
            self.metrics = {k: v for k, v in self.metrics.items() if not k.startswith("val/")}
            self._sample_rewards.clear()
        else:
            self.metrics = {"n_interactions": self._total_number_interactions}

    def post_evaluate(self, ep: int) -> None:
        if len(self._eval_rewards) > 0:
            cur = {
                "val/n_steps": sum([n for n, _ in self._eval_rewards]),
                "val/n_segment": len(self._eval_rewards),
                "val/avg_reward": np.mean([r for _, r in self._eval_rewards]),
                "val/avg_n_steps": np.mean([n for n, _ in self._eval_rewards]),
                "val/max_n_steps": np.max([n for n, _ in self._eval_rewards]),
            }
            self.metrics.update(cur)
            self._eval_rewards.clear()
        else:
            self.metrics = {k: v for k, v in self.metrics.items() if not k.startswith("val/")}

    @staticmethod
    def merge_metrics(metrics_list: List[dict]) -> dict:
        metrics = {"n_interactions": sum(m["n_interactions"] for m in metrics_list)}

        tmp_metrics_list = [m for m in metrics_list if "n_steps" in m]
        if len(tmp_metrics_list) > 0:
            n_steps = sum(m["n_steps"] for m in tmp_metrics_list)
            n_segment = sum(m["n_segment"] for m in tmp_metrics_list)
            metrics.update(
                {
                    "n_steps": n_steps,
                    "n_segment": n_segment,
                    "avg_reward": sum(m["avg_reward"] * m["n_segment"] for m in tmp_metrics_list) / n_segment,
                    "avg_n_steps": n_steps / n_segment,
                    "max_n_steps": max(m["max_n_steps"] for m in tmp_metrics_list),
                },
            )

        tmp_metrics_list = [m for m in metrics_list if "val/n_steps" in m]
        if len(tmp_metrics_list) > 0:
            n_steps = sum(m["val/n_steps"] for m in tmp_metrics_list)
            n_segment = sum(m["val/n_segment"] for m in tmp_metrics_list)
            metrics.update(
                {
                    "val/n_steps": n_steps,
                    "val/n_segment": n_segment,
                    "val/avg_reward": sum(m["val/avg_reward"] * m["val/n_segment"] for m in tmp_metrics_list)
                    / n_segment,
                    "val/avg_n_steps": n_steps / n_segment,
                    "val/max_n_steps": max(m["val/max_n_steps"] for m in tmp_metrics_list),
                },
            )

        return metrics
