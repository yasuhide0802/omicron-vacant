# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from abc import ABC, abstractmethod
import os
import pickle

import torch

from maro.rl.algorithms.torch.abs_algorithm import AbsAlgorithm
from maro.rl.storage.abs_store import AbsStore


class AbsAgent(ABC):
    """Abstract RL agent class.

    It's a sandbox for the RL algorithm. Scenario-specific details will be excluded.
    We focus on the abstraction algorithm development here. Environment observation and decision events will
    be converted to a uniform format before calling in. And the output will be converted to an environment
    executable format before return back to the environment. Its key responsibility is optimizing policy based
    on interaction with the environment.

    Args:
        name (str): Agent's name.
        algorithm (AbsAlgorithm): A concrete algorithm instance that inherits from AbstractAlgorithm.
            This is the centerpiece of the Agent class and is responsible for the most important tasks of an agent:
            choosing actions and optimizing models.
        experience_pool (AbsStore): A data store that stores experiences generated by the experience shaper.
    """
    def __init__(self,
                 name: str,
                 algorithm: AbsAlgorithm,
                 experience_pool: AbsStore
                 ):
        self._name = name
        self._algorithm = algorithm
        self._experience_pool = experience_pool

    @property
    def algorithm(self):
        """Underlying algorithm employed by the agent."""
        return self._algorithm

    @property
    def experience_pool(self):
        """Underlying experience pool where the agent stores experiences."""
        return self._experience_pool

    def choose_action(self, model_state, epsilon: float = .0):
        """Choose an action using the underlying algorithm based on a preprocessed env state.

        Args:
            model_state: State vector as accepted by the underlying algorithm.
            epsilon (float): Exploration rate.
        Returns:
            Action given by the underlying policy model.
        """
        return self._algorithm.choose_action(model_state, epsilon)

    @abstractmethod
    def train(self):
        """Training logic to be implemented by the user.

        For example, this may include drawing samples from the experience pool and the algorithm training on
        these samples.
        """
        return NotImplementedError

    def store_experiences(self, experiences):
        """Store new experiences in the experience pool."""
        self._experience_pool.put(experiences)

    def load_model_dict(self, model_dict: dict):
        """Load models from memory."""
        self._algorithm.model_dict = model_dict

    def load_model_dict_from_file(self, file_path):
        """Load models from a disk file."""
        model_dict = torch.load(file_path)
        for model_key, state_dict in model_dict.items():
            self._algorithm.model_dict[model_key].load_state_dict(state_dict)

    def dump_model_dict(self, dir_path: str):
        """Dump models to disk."""
        torch.save({model_key: model.state_dict() for model_key, model in self._algorithm.model_dict.items()},
                   os.path.join(dir_path, self._name))

    def dump_experience_store(self, dir_path: str):
        """Dump the experience pool to disk."""
        path = os.path.join(dir_path, self._name)
        os.makedirs(path, exist_ok=True)
        with open(path, "w") as fp:
            pickle.dump(self._experience_pool, fp)
