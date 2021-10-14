# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import importlib
import os
import sys

from maro.rl.learning import DistributedPolicyManager, MultiProcessPolicyManager, SimplePolicyManager
from maro.rl.workflows.helpers import from_env, get_default_log_dir

sys.path.insert(0, from_env("SCENARIODIR"))
module = importlib.import_module(from_env("SCENARIO"))
policy_func_dict = getattr(module, "policy_func_dict")
agent2policy = getattr(module, "agent2policy")

checkpoint_dir = from_env("CHECKPOINTDIR", required=False, default=None)
if checkpoint_dir:
    os.makedirs(checkpoint_dir, exist_ok=True)
load_policy_dir = from_env("LOADDIR", required=False, default=None)
log_dir = from_env("LOGDIR", required=False, default=get_default_log_dir(from_env("JOB")))
os.makedirs(log_dir, exist_ok=True)


def get_policy_manager():
    manager_type = from_env("POLICYMANAGERTYPE")
    data_parallel = os.getenv("DATAPARALLEL") == "True"
    if data_parallel:
        num_grad_workers = int(os.getenv("NUMGRADWORKERS", default=1))
        group = from_env("POLICYGROUP")
    else:
        num_grad_workers = 1
        group = None
    proxy_kwargs = {
        "redis_address": (from_env("REDISHOST"), from_env("REDISPORT")),
        "max_peer_discovery_retries": 50
    }
    if manager_type == "simple":
        return SimplePolicyManager(
            policy_func_dict,
            load_dir=load_policy_dir,
            checkpoint_dir=checkpoint_dir,
            data_parallelism=num_grad_workers,
            group=group,
            proxy_kwargs=proxy_kwargs,
            log_dir=log_dir
        )
    elif manager_type == "multi-process":
        return MultiProcessPolicyManager(
            policy_func_dict,
            load_dir=load_policy_dir,
            checkpoint_dir=checkpoint_dir,
            data_parallelism=num_grad_workers,
            group=group,
            proxy_kwargs=proxy_kwargs,
            log_dir=log_dir
        )
    elif manager_type == "distributed":
        return DistributedPolicyManager(
            list(policy_func_dict.keys()), from_env("NUMHOSTS"),
            group=from_env("POLICYGROUP"),
            data_parallelism=num_grad_workers,
            proxy_kwargs=proxy_kwargs,
            log_dir=log_dir
        )

    raise ValueError(
        f"Unsupported policy manager type: {manager_type}. Supported modes: simple, multi-process, distributed"
    )


if __name__ == "__main__":
    policy_manager = get_policy_manager()
    policy_manager.server(
        from_env("GROUP"),
        from_env("NUMROLLOUTS"),
        max_lag=from_env("MAXLAG", required=False, default=0),
        proxy_kwargs={
            "redis_address": (from_env("REDISHOST"), from_env("REDISPORT")),
            "max_peer_discovery_retries": 50
        },
        log_dir=log_dir
    )
