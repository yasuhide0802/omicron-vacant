import torch
import torch.nn.functional as functional
from torch import optim
from .base_agent import BaseAgent
from .replay_buffer import Replay_Buffer
from .exploration import OU_Noise_Exploration
import os
from shutil import copy2

from examples.hvac.rl.sac_policy import create_NN

class DDPG(BaseAgent):
    """A DDPG Agent"""
    agent_name = "DDPG"

    def __init__(self, config, env, logger):
        BaseAgent.__init__(self, config, env, logger)
        self.hyperparameters = config.hyperparameters
        self.critic_local = create_NN(
            input_dim=self.state_size + self.action_size,
            output_dim=1,
            hyperparameters=self.hyperparameters["Critic"],
            seed=self.hyperparameters["Critic"]["base_seed"],
            device=self.device
        )
        self.critic_target = create_NN(
            input_dim=self.state_size + self.action_size,
            output_dim=1,
            hyperparameters=self.hyperparameters["Critic"],
            seed=self.hyperparameters["Critic"]["base_seed"],
            device=self.device
        )
        BaseAgent.copy_model_over(self.critic_local, self.critic_target)

        self.critic_optimizer = optim.Adam(self.critic_local.parameters(),
                                           lr=self.hyperparameters["Critic"]["learning_rate"], eps=1e-4)
        self.memory = Replay_Buffer(
            self.config.replay_memory_config["capacity"],
            self.config.replay_memory_config["batch_size"]
        )
        self.actor_local = create_NN(
            input_dim=self.state_size,
            output_dim=self.action_size,
            hyperparameters=self.hyperparameters["Actor"],
            seed=self.hyperparameters["Actor"]["seed"],
            device=self.device
        )
        self.actor_target = create_NN(
            input_dim=self.state_size,
            output_dim=self.action_size,
            hyperparameters=self.hyperparameters["Actor"],
            seed=self.hyperparameters["Actor"]["seed"],
            device=self.device
        )
        BaseAgent.copy_model_over(self.actor_local, self.actor_target)

        self.actor_optimizer = optim.Adam(self.actor_local.parameters(),
                                          lr=self.hyperparameters["Actor"]["learning_rate"], eps=1e-4)
        self.exploration_strategy = OU_Noise_Exploration(self.config)

    def step(self):
        """Runs a step in the game"""
        while not self.done:
            # print("State ", self.state.shape)
            self.action = self.pick_action()
            self.conduct_action(self.action)
            self.memory.add_experience(self.state, self.action, self.reward, self.next_state, self.done)
            self.state = self.next_state #this is to set the state for the next iteration
            self.env_step_number += 1

        for _ in range(2):
            states, actions, rewards, next_states, dones = self.sample_experiences()
            self.critic_learn(states, actions, rewards, next_states, dones)
            self.actor_learn(states)

    def sample_experiences(self):
        return self.memory.sample()

    def pick_action(self, state=None):
        """Picks an action using the actor network and then adds some noise to it to ensure exploration"""
        if state is None: state = torch.from_numpy(self.state).float().unsqueeze(0).to(self.device)
        else:
            state = torch.FloatTensor([state]).to(self.device)
        self.actor_local.eval()
        with torch.no_grad():
            action = self.actor_local(state).cpu().data.numpy()
        self.actor_local.train()
        action = self.exploration_strategy.perturb_action_for_exploration_purposes({"action": action})
        return action.squeeze(0)

    def critic_learn(self, states, actions, rewards, next_states, dones):
        """Runs a learning iteration for the critic"""
        loss = self.compute_loss(states, next_states, rewards, actions, dones)
        self._take_optimization_step(self.critic_optimizer, self.critic_local, loss, self.hyperparameters["Critic"]["gradient_clipping_norm"])
        self._soft_update_of_target_network(self.critic_local, self.critic_target, self.hyperparameters["Critic"]["tau"])

    def compute_loss(self, states, next_states, rewards, actions, dones):
        """Computes the loss for the critic"""
        with torch.no_grad():
            critic_targets = self.compute_critic_targets(next_states, rewards, dones)
        critic_expected = self.compute_expected_critic_values(states, actions)
        loss = functional.mse_loss(critic_expected, critic_targets)
        return loss

    def compute_critic_targets(self, next_states, rewards, dones):
        """Computes the critic target values to be used in the loss for the critic"""
        critic_targets_next = self.compute_critic_values_for_next_states(next_states)
        critic_targets = self.compute_critic_values_for_current_states(rewards, critic_targets_next, dones)
        return critic_targets

    def compute_critic_values_for_next_states(self, next_states):
        """Computes the critic values for next states to be used in the loss for the critic"""
        with torch.no_grad():
            actions_next = self.actor_target(next_states)
            critic_targets_next = self.critic_target(torch.cat((next_states, actions_next), 1))
        return critic_targets_next

    def compute_critic_values_for_current_states(self, rewards, critic_targets_next, dones):
        """Computes the critic values for current states to be used in the loss for the critic"""
        critic_targets_current = rewards + (self.hyperparameters["ddpg"]["reward_discount"] * critic_targets_next * (1.0 - dones))
        return critic_targets_current

    def compute_expected_critic_values(self, states, actions):
        """Computes the expected critic values to be used in the loss for the critic"""
        critic_expected = self.critic_local(torch.cat((states, actions), 1))
        return critic_expected

    def time_for_critic_and_actor_to_learn(self):
        """Returns boolean indicating whether there are enough experiences to learn from and it is time to learn for the
        actor and critic"""
        return (
            len(self.memory) > self.config.replay_memory_config["batch_size"]
            and self.env_step_number % self.hyperparameters["update_every_n_steps"] == 0
        )

    def actor_learn(self, states):
        """Runs a learning iteration for the actor"""
        actor_loss = self.calculate_actor_loss(states)
        self._take_optimization_step(self.actor_optimizer, self.actor_local, actor_loss,
                                    self.hyperparameters["Actor"]["gradient_clipping_norm"])
        self._soft_update_of_target_network(self.actor_local, self.actor_target, self.hyperparameters["Actor"]["tau"])

    def calculate_actor_loss(self, states):
        """Calculates the loss for the actor"""
        actions_pred = self.actor_local(states)
        actor_loss = -self.critic_local(torch.cat((states, actions_pred), 1)).mean()
        return actor_loss

    def save_model(self):
        torch.save(
            self.actor_local.state_dict(),
            os.path.join(self.config.checkpoint_dir, f"actor_{self.episode_number}.pt")
        )
        torch.save(
            self.actor_optimizer.state_dict(),
            os.path.join(self.config.checkpoint_dir, f"actor_optimizer_{self.episode_number}.pt")
        )

        copy2(
            os.path.join(self.config.checkpoint_dir, f"actor_{self.episode_number}.pt"),
            os.path.join(self.config.checkpoint_dir, "actor.pt")
        )
        copy2(
            os.path.join(self.config.checkpoint_dir, f"actor_optimizer_{self.episode_number}.pt"),
            os.path.join(self.config.checkpoint_dir, "actor_optimizer.pt")
        )

    def load_model(self):
        self.actor_local.load_state_dict(torch.load(os.path.join(self.config.checkpoint_dir, "actor.pt")))
        self.actor_optimizer.load_state_dict(torch.load(os.path.join(self.config.checkpoint_dir, "actor_optimizer.pt")))
