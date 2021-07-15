# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import time

from os import makedirs
from os.path import dirname, join, realpath

from maro.utils import Logger

log_dir = join(dirname(realpath(__file__)), "log", str(time.time()))
makedirs(log_dir, exist_ok=True)

simulation_logger = Logger("SIMUALTION", dump_folder=log_dir)

def post_episode_callback(trackers):
    # print the env metric from each rollout worker
    for tracker in trackers:
        simulation_logger.info(f"env metric: {tracker['env_metric']}")

    # print the average env metric
    if len(trackers) > 1:
        metric_keys, num_trackers = trackers[0]["env_metric"].keys(), len(trackers)
        avg_metric = {key: sum(tr["env_metric"][key] for tr in trackers) / num_trackers for key in metric_keys}
        simulation_logger.info(f"average env metric: {avg_metric}")


post_collect = post_episode_callback
post_evaluate = post_episode_callback
