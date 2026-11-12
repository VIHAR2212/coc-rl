from stable_baselines3 import PPO
from sim import CoCEnv

env = CoCEnv()
model = PPO("MultiInputPolicy", env, verbose=1, tensorboard_log="runs/")
model.learn(total_timesteps=200_000)
model.save("models/ppo_coc_v0")
