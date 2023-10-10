from abc import ABC
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from Utils.Tensorboard_Callbacks import TensorboardCallback
from BaseEnvironment import BaseEnvironment
import numpy as np
import pickle
from Utils.Scalers import VectorScaler


class PPO_Environment(BaseEnvironment, ABC):

    def __init__(self, id_number, graphics, scaler, obs_space, include_affect, path):
        super().__init__(id_number, graphics, scaler, obs_space, include_affect, path)

        self.max_reward = 0
        self.cumulative_reward = 0
        self.reward = 0
        self.episode_length = 0
        self.last_x = np.round(self.reset()[0])
        self.max_x = -np.inf

    def calculate_reward(self, state, env_score):
        current_x = np.round(state[0])
        reward = 0

        print(state)

        if state[3] == 0:
            reward -= 10

        if current_x < self.last_x:
            reward -= 1
        elif current_x > self.last_x:
            reward += 1
            if current_x > self.max_x:
                reward += 1

        self.last_x = current_x
        self.reward = (self.score - env_score) + reward
        self.score = env_score

    def reset_condition(self):
        self.episode_length += 1
        if self.episode_length > 4 * 140:
            self.episode_length = 0
            self.max_x = -np.inf
            self.create_and_send_message("[Cell Name]:Seed")
            self.reset()

    def reset(self):
        super().reset()
        self.cumulative_reward = 0
        return self.tuple_to_vector(self.env.reset())[2:]

    def update_stats(self):
        self.cumulative_reward += self.reward
        self.max_score = np.max([self.score, self.max_score])
        self.max_reward = np.max([self.max_reward, self.reward])

    def step(self, action):
        # Move the env forward 1 tick and receive messages through side-channel.
        state, env_score, d, info = self.env.step((action[0] - 1, action[1]))
        state = state[0][2:]
        self.calculate_reward(state, env_score)
        self.update_stats()
        self.reset_condition()
        return state, self.reward, d, info

    def handle_level_end(self):
        print("End of level reached, resetting environment.")
        self.reset()


if __name__ == "__main__":

    load_scaler = False
    if load_scaler:
        with open('../Models_Pkls/MinMaxScaler.pkl', 'rb') as f:
            scaler = pickle.load(f)
    else:
        scaler = VectorScaler(49)

    env = DummyVecEnv([lambda: PPO_Environment(counter,
                                               graphics=True,
                                               scaler=None,
                                               include_affect=False,
                                               obs_space={"low": -np.inf, "high": np.inf, "shape": (68,)},
                                               path="./Builds/Platformer_Windows/Platform.exe") for counter in [1]])
    sideChannel = env.envs[0].customSideChannel
    model = PPO("MlpPolicy", env=env, tensorboard_log="./Tensorboard")
    model.learn(total_timesteps=1500000, progress_bar=True, callback=TensorboardCallback(), tb_log_name="PPO")
    model.save("ppo_solid_test")

    with open("../Models_Pkls/MinMaxScaler.pkl", 'wb') as f:
        pickle.dump(scaler, f)
