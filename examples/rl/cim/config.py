# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.


env_conf = {
    "scenario": "cim",
    "topology": "toy.4p_ssdd_l0.0",
    "durations": 560
}

port_attributes = ["empty", "full", "on_shipper", "on_consignee", "booking", "shortage", "fulfillment"]
vessel_attributes = ["empty", "full", "remaining_space"]

state_shaping_conf = {
    "look_back": 7,
    "max_ports_downstream": 2
}

action_shaping_conf = {
    "action_space": [(i - 10) / 10 for i in range(21)],
    "finite_vessel_space": True,
    "has_early_discharge": True
}

reward_shaping_conf = {
    "time_window": 99,
    "fulfillment_factor": 1.0,
    "shortage_factor": 1.0,
    "time_decay": 0.97
}

# obtain state dimension from a temporary env_wrapper instance
state_dim = (
    (state_shaping_conf["look_back"] + 1) * (state_shaping_conf["max_ports_downstream"] + 1) * len(port_attributes)
    + len(vessel_attributes)
)

# DQN settings
q_net_conf = {
    "network": {
        "input_dim": state_dim,
        "hidden_dims": [256, 128, 64, 32],
        "output_dim": len(action_shaping_conf["action_space"]),
        "activation": "leaky_relu",
        "softmax": False,
        "batch_norm": True,
        "skip_connection": False,
        "head": True,
        "dropout_p": 0.0
    },
    "optimization": {
        "optim_cls": "rmsprop",
        "optim_params": {"lr": 0.05}
    }
}

dqn_conf = {
    "reward_discount": .0,
    "update_target_every": 5,
    "num_epochs": 10,
    "soft_update_coeff": 0.1,
    "double": False,
    "replay_memory_capacity": 10000,
    "random_overwrite": False,
    "rollout_batch_size": 128,
    "train_batch_size": 32,
    # "prioritized_replay_kwargs": {
    #     "alpha": 0.6,
    #     "beta": 0.4,
    #     "beta_step": 0.001,
    #     "max_priority": 1e8
    # }
}

exploration_conf = {
    "last_ep": 10,
    "initial_value": 0.4,
    "final_value": 0.0,
    "splits": [(5, 0.32)]
}


# AC settings
ac_net_conf = {
    "network": {
        "actor": {
            "input_dim": state_dim,
            "hidden_dims": [256, 128, 64],
            "output_dim": len(action_shaping_conf["action_space"]),
            "activation": "tanh",
            "softmax": True,
            "batch_norm": False,
            "head": True
        },
        "critic": {
            "input_dim": state_dim,
            "hidden_dims": [256, 128, 64],
            "output_dim": 1,
            "activation": "leaky_relu",
            "softmax": False,
            "batch_norm": True,
            "head": True
        }
    },
    "optimization": {
        "actor": {
            "optim_cls": "adam",
            "optim_params": {"lr": 0.001}
        },
        "critic": {
            "optim_cls": "rmsprop",
            "optim_params": {"lr": 0.001}
        }
    }
}

ac_conf = {
    "reward_discount": .0,
    "grad_iters": 10,
    "critic_loss_cls": "smooth_l1",
    "min_logp": None,
    "critic_loss_coeff": 0.1,
    "entropy_coeff": 0.01,
    # "clip_ratio": 0.8   # for PPO
    "lam": 0.9,
    "get_loss_on_rollout": True
}