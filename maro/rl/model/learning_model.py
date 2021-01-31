# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from abc import abstractmethod
from collections import namedtuple
from typing import Dict, List, Union

import torch
import torch.nn as nn

from maro.utils import clone
from maro.utils.exception.rl_toolkit_exception import MissingOptimizer

OptimOption = namedtuple(
    "OptimOption", ["optim_cls", "optim_params", "scheduler_cls", "scheduler_params"],
    defaults=[None, None]    
)


class AbsLearningModel(nn.Module):
    """Trainable model that consists of multiple network components.

    Args:
        component (Union[nn.Module, Dict[str, nn.Module]]): Network component(s) comprising the model.
        optim_option (Union[OptimOption, Dict[str, OptimOption]]): Optimizer options for the components.
            Each option consists of an optimizer class (which is a subclass of torch.optim.Optimizer) and its
            corresponding optimizer parameters and optionally the scheduler class and parameters. If none, no
            optimizer will be created for the model which means the model is not trainable. If it is a single
            OptimOption instance, an optimizer will be created to jointly optimize all parameters of the model.
            If it is a dictionary, for each `(key, value)` pair, an optimizer specified by `value` will be
            created for the internal component named `key`. Note that it is possible to freeze certain components
            while optimizing others by providing a subset of the keys in ``component``. Defaults to None.
    """
    def __init__(
        self,
        component: Union[nn.Module, Dict[str, nn.Module]],
        optim_option: Union[OptimOption, Dict[str, OptimOption]] = None
    ):
        super().__init__()
        assert (
            optim_option is None
            or isinstance(optim_option, OptimOption)
            or isinstance(component, dict)
        )
        self._component = component if isinstance(component, nn.Module) else nn.ModuleDict(component)
        self._is_trainable = optim_option is not None
        if self._is_trainable:
            if isinstance(optim_option, OptimOption):
                self._optimizer = optim_option.optim_cls(self.parameters(), **optim_option.optim_params)
                if optim_option.scheduler_cls:
                    self._scheduler = optim_option.scheduler_cls(self._optimizer, **optim_option.scheduler_params)
                else:
                    self._scheduler = None
            else:
                self._optimizer = {
                    name: opt.optim_cls(self._component[name].parameters(), **opt.optim_params)
                    for name, opt in optim_option.items()
                }
                self._scheduler = {
                    name: opt.scheduler_cls(self._optimizer[name], **opt.scheduler_params)
                    for name, opt in optim_option.items() if opt.scheduler_cls
                }
        else:
            self.eval()
            for param in self.parameters():
                param.requires_grad = False

    def __getstate__(self):
        dic = self.__dict__.copy()
        if "_optimizer" in dic:
            del dic["_optimizer"]
        dic["_is_trainable"] = False
        return dic

    def __setstate__(self, dic: dict):
        self.__dict__ = dic

    @property
    def is_trainable(self) -> bool:
        return self._is_trainable

    @abstractmethod
    def forward(self, *args, **kwargs):
        raise NotImplementedError

    def learn(self, loss):
        """Use the loss to back-propagate gradients and apply them to the underlying parameters."""
        if not self._is_trainable:
            raise MissingOptimizer("No optimizer registered to the model")
        if isinstance(self._optimizer, dict):
            for optimizer in self._optimizer.values():
                optimizer.zero_grad()
        else:
            self._optimizer.zero_grad()

        # Obtain gradients through back-propagation
        loss.backward()

        # Apply gradients
        if isinstance(self._optimizer, dict):
            for optimizer in self._optimizer.values():
                optimizer.step()
        else:
            self._optimizer.step()

    def update_learning_rate(self, component_name: Union[str, List[str]] = None):
        if not isinstance(self._scheduler, dict):
            self._scheduler.step()
        elif isinstance(component_name, str):
            self._scheduler[component_name].step()
        elif isintance(component_name, list):
            for key in component_name:
                self._scheduler[key].step()
        else:
            for sch in self._scheduler.values():
                sch.step()

    def soft_update(self, other_model: nn.Module, tau: float):
        for params, other_params in zip(self.parameters(), other_model.parameters()):
            params.data = (1 - tau) * params.data + tau * other_params.data

    def copy(self):
        return clone(self)

    def load(self, state_dict):
        self.load_state_dict(state_dict)

    def dump(self):
        return self.state_dict()

    def load_from_file(self, path: str):
        self.load_state_dict(torch.load(path))

    def dump_to_file(self, path: str):
        torch.save(self.state_dict(), path)


class SimpleMultiHeadModel(AbsLearningModel):
    """A compound network structure that consists of multiple task heads and an optional shared stack.

    Args:
        component (Union[nn.Module, Dict[str, nn.Module]]): Network component(s) comprising the model.
            All components must have the same input dimension except the one designated as the shared
            component by ``shared_component_name``.
        optim_option (Union[OptimOption, Dict[str, OptimOption]]): Optimizer option for
            the components. Defaults to None.
        shared_component_name (str): Name of the network component to be designated as the shared component at the
            bottom of the architecture. Must be None or a key in ``component``. If only a single component
            is present, this is ignored. Defaults to None.
    """
    def __init__(
        self,
        component: Union[nn.Module, Dict[str, nn.Module]],
        optim_option: Union[OptimOption, Dict[str, OptimOption]] = None,
        shared_component_name: str = None
    ):
        super().__init__(component, optim_option=optim_option)
        if isinstance(component, dict):
            if shared_component_name is not None:
                assert (shared_component_name in component), (
                    f"shared_component_name must be one of {list(component.keys())}, got {shared_component_name}"
                )
            self._task_names = [name for name in component if name != shared_component_name]
        else:
            self._task_names = None
        self._shared_component_name = shared_component_name

    @property
    def task_names(self):
        return self._task_names

    def _forward(self, inputs, task_name: str = None):
        if not isinstance(self._component, nn.ModuleDict):
            return self._component(inputs)

        if self._shared_component_name is not None:
            inputs = self._component[self._shared_component_name](inputs)  # features

        if task_name is None:
            return {name: self._component[name](inputs) for name in self._task_names}

        if isinstance(task_name, list):
            return {name: self._component[name](inputs) for name in task_name}
        else:
            return self._component[task_name](inputs)

    def forward(self, inputs, task_name: Union[str, List[str]] = None, is_training: bool = True):
        """Feedforward computations for the given head(s).

        Args:
            inputs: Inputs to the model.
            task_name (str): The name of the task for which the network output is required. If the model contains only
                one task module, the task_name is ignored and the output of that module will be returned. If the model
                contains multiple task modules, then 1) if task_name is None, the output from all task modules will be
                returned in the form of a dictionary; 2) if task_name is a list, the outputs from the task modules
                specified in the list will be returned in the form of a dictionary; 3) if this is a single string,
                the output from the corresponding task module will be returned.
            is_training (bool): If true, all torch submodules will be set to training mode, and auto-differentiation
                will be turned on. Defaults to True.

        Returns:
            Outputs from the required head(s).
        """
        self.train(mode=is_training)
        if is_training:
            return self._forward(inputs, task_name)

        with torch.no_grad():
            return self._forward(inputs, task_name)
