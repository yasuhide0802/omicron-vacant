# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from types import ModuleType
from typing import Callable, Dict

from maro.rl.policy import RLPolicy
from maro.rl.rollout import AbsEnvSampler
from maro.rl.training import AbsTrainer
from maro.rl.utils.common import from_env


class ScenarioAttr(object):
    """Helper class to read scenario attributes from the environment. Attributes that retrieved through
    ScenarioAttr could have more clear type hints.
    """
    def __init__(self, scenario_module: ModuleType) -> None:
        super(ScenarioAttr, self).__init__()
        self._scenario_module = scenario_module

    def get_env_sampler(self, policy_creator: Dict[str, Callable[[str], RLPolicy]]) -> AbsEnvSampler:
        return getattr(self._scenario_module, "env_sampler_creator")(policy_creator)

    @property
    def agent2policy(self) -> Dict[str, str]:
        return getattr(self._scenario_module, "agent2policy")

    @property
    def policy_creator(self) -> Dict[str, Callable[[str], RLPolicy]]:
        return getattr(self._scenario_module, "policy_creator")

    @property
    def trainer_creator(self) -> Dict[str, Callable[[str], AbsTrainer]]:
        return getattr(self._scenario_module, "trainer_creator")

    @property
    def post_collect(self) -> Callable[[list, int, int], None]:
        return getattr(self._scenario_module, "post_collect", None)

    @property
    def post_evaluate(self) -> Callable[[list, int], None]:
        return getattr(self._scenario_module, "post_evaluate", None)


def _get_scenario_path() -> str:
    return str(from_env("SCENARIO_PATH"))
