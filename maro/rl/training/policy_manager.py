# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import time
from abc import ABC, abstractmethod
from collections import defaultdict
from os import getcwd
from typing import Dict, List

from maro.communication import Proxy, SessionType
from maro.rl.experience import ExperienceSet
from maro.rl.policy import AbsCorePolicy, AbsPolicy
from maro.utils import Logger

from .message_enums import MsgKey, MsgTag


class AbsPolicyManager(ABC):
    """Controller for policy updates.

    The actual policy instances may reside here or be distributed on a set of remote nodes.
    """
    def __init__(self):
        pass

    @property
    @abstractmethod
    def names(self):
        """Return the list of policy names."""
        raise NotImplementedError

    @abstractmethod
    def on_experiences(self, exp_by_policy: Dict[str, ExperienceSet]):
        """Logic for handling incoming experiences is implemented here."""
        raise NotImplementedError

    @abstractmethod
    def get_state(self):
        """Return the latest policy states."""
        raise NotImplementedError


class LocalPolicyManager(AbsPolicyManager):
    """Policy manager that contains the actual policy instances.

    Args:
        policies (List[AbsPolicy]): A list of policies.
        log_dir (str): Directory to store logs in. A ``Logger`` with tag "LEARNER" will be created at init time
            and this directory will be used to save the log files generated by it. Defaults to the current working
            directory.
    """
    def __init__(self, policies: List[AbsPolicy], log_dir: str = getcwd()):
        super().__init__()
        self._names = [policy.name for policy in policies]
        self._logger = Logger("LOCAL_POLICY_MANAGER", dump_folder=log_dir)
        self.policy_dict = {policy.name: policy for policy in policies}
        self._new_exp_counter = defaultdict(int)

    @property
    def names(self):
        return self._names

    def on_experiences(self, exp_by_policy: Dict[str, ExperienceSet]):
        """Store experiences and update policies if possible.

        The incoming experiences are expected to be grouped by policy ID and will be stored in the corresponding
        policy's experience manager. Policies whose update conditions have been met will then be updated.
        """
        t0 = time.time()
        updated = {
            name: self.policy_dict[name].get_state()
            for name, exp in exp_by_policy.items()
            if isinstance(self.policy_dict[name], AbsCorePolicy) and self.policy_dict[name].on_experiences(exp)
        }

        if updated:
            self._logger.info(f"Updated policies {list(updated.keys())}")

        self._logger.debug(f"policy update time: {time.time() - t0}")
        return updated

    def get_state(self):
        return {name: policy.get_state() for name, policy in self.policy_dict.items()}


class ParallelPolicyManager(AbsPolicyManager):
    def __init__(
        self,
        policy2server: Dict[str, str],
        group: str,
        log_dir: str = getcwd(),
        **proxy_kwargs
    ):
        super().__init__()
        self._logger = Logger("PARALLEL_POLICY_MANAGER", dump_folder=log_dir)
        self.policy2server = policy2server
        self._names = list(self.policy2server.keys())
        peers = {"policy_server": len(set(self.policy2server.values()))}
        self._proxy = Proxy(group, "policy_manager", peers, **proxy_kwargs)

    @property
    def names(self):
        return self._names

    def on_experiences(self, exp_by_policy: Dict[str, ExperienceSet]):
        msg_body_by_dest, policy_state_dict = defaultdict(dict), {}
        for policy_name, exp in exp_by_policy.items():
            policy_server_id = self.policy2server[policy_name]
            if MsgKey.EXPERIENCES not in msg_body_by_dest[policy_server_id]:
                msg_body_by_dest[policy_server_id][MsgKey.EXPERIENCES] = {}
            msg_body_by_dest[policy_server_id][MsgKey.EXPERIENCES][policy_name] = exp

        for reply in self._proxy.scatter(MsgTag.TRAIN, SessionType.TASK, list(msg_body_by_dest.items())):
            for policy_name, policy_state in reply.body[MsgKey.POLICY].items():
                policy_state_dict[policy_name] = policy_state

        return policy_state_dict

    def get_state(self):
        policy_state_dict = {}
        for reply in self._proxy.broadcast("policy_server", MsgTag.GET_POLICY_STATE, SessionType.TASK):
            for policy_name, policy_state in reply.body[MsgKey.POLICY].items():
                policy_state_dict[policy_name] = policy_state

        return policy_state_dict

    def exit(self):
        """Tell the remote actors to exit."""
        self._proxy.ibroadcast("policy_server", MsgTag.EXIT, SessionType.NOTIFICATION)
        self._proxy.close()
        self._logger.info("Exiting...")
