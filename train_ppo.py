"""Train MaskablePPO on single base first, then train split, with TensorBoard & reward curves."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv

from sim.rl_wrapper import ActionMaskCoCEnv, CoCFeatureExtractor, TRAIN_BASES


def _mask_fn(env):
    return env.action_masks()


def make_masked_env(bases, shaping_mode="baseline"):
    env = ActionMaskCoCEnv(bases=bases, shaping_mode=shaping_mode)
    env = ActionMasker(env, _mask_fn)
    return Monitor(env)


class EpisodeMetricsCallback(BaseCallback):
    """Collect per-episode reward and destruction % for reward curve plotting."""

    def __init__(self):
        super().__init__()
        self.ep_rewards: list[float] = []
        self.ep_destructions: list[float] = []
        self._running_rew = 0.0

    def _on_step(self) -> bool:
        rewards = self.locals.get("rewards", [])
        dones = self.locals.get("dones", [])
        infos = self.locals.get("infos", [])
        if len(rewards) > 0:
            self._running_rew += float(rewards[0])
            if dones[0]:
                self.ep_rewards.append(self._running_rew)
                self.ep_destructions.append(float(infos[0].get("destruction", 0.0)) * 100.0)
                self._running_rew = 0.0
        return True


def _rolling(vals: list[float], window: int = 10) -> np.ndarray:
    if not vals:
        return np.array([], dtype=np.float32)
    arr = np.asarray(vals, dtype=np.float32)
    out = np.empty_like(arr)
    for i in range(len(arr)):
        lo = max(0, i - window + 1)
        out[i] = float(np.mean(arr[lo : i + 1]))
    return out


def save_reward_curves(
    s1_rew: list[float],
    s1_dest: list[float],
    s2_rew: list[float],
    s2_dest: list[float],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    panels = [
        (axes[0, 0], s1_rew, "Stage 1 (base03): Episode Reward", "Reward"),
        (axes[0, 1], s1_dest, "Stage 1 (base03): Destruction %", "Destruction (%)"),
        (axes[1, 0], s2_rew, "Stage 2 (Train Split): Episode Reward", "Reward"),
        (axes[1, 1], s2_dest, "Stage 2 (Train Split): Destruction %", "Destruction (%)"),
    ]
    for ax, vals, title, ylabel in panels:
        if vals:
            xs = np.arange(1, len(vals) + 1)
            ax.plot(xs, vals, alpha=0.3, label="Episode")
            ax.plot(xs, _rolling(vals, 15), linewidth=2.0, label="Rolling Mean (15)")
            ax.legend(fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Episode")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def train_pipeline(
    single_base: str = "base03.json",
    train_bases: list[str] | None = None,
    stage1_steps: int = 20_000,
    stage2_steps: int = 60_000,
    shaping_mode: str = "baseline",
    model_out: Path = Path("models/ppo_coc_v1.zip"),
    curve_out: Path = Path("results/reward_curves.png"),
    seed: int = 42,
):
    train_bases = train_bases or list(TRAIN_BASES)
    model_out.parent.mkdir(parents=True, exist_ok=True)

    policy_kwargs = dict(
        features_extractor_class=CoCFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=160),
        net_arch=dict(pi=[128, 64], vf=[128, 64]),
    )

    print(f"=== Stage 1: Single-base training ({single_base}, {stage1_steps} steps) ===", flush=True)
    env1 = DummyVecEnv([lambda: make_masked_env([single_base], shaping_mode=shaping_mode)])
    cb1 = EpisodeMetricsCallback()
    model = MaskablePPO(
        "MultiInputPolicy",
        env1,
        learning_rate=3e-4,
        n_steps=1024,
        batch_size=128,
        n_epochs=6,
        gamma=0.99,
        ent_coef=0.02,
        policy_kwargs=policy_kwargs,
        tensorboard_log="runs/",
        seed=seed,
        verbose=1,
    )
    model.learn(total_timesteps=stage1_steps, callback=cb1, tb_log_name="m7_stage1_single")
    stage1_path = model_out.parent / "ppo_stage1_single.zip"
    model.save(stage1_path)
    env1.close()

    print(f"=== Stage 2: Train-split training ({train_bases}, {stage2_steps} steps) ===", flush=True)
    env2 = DummyVecEnv([lambda: make_masked_env(train_bases, shaping_mode=shaping_mode)])
    cb2 = EpisodeMetricsCallback()
    model.set_env(env2)
    model.learn(
        total_timesteps=stage2_steps,
        callback=cb2,
        tb_log_name="m7_stage2_split",
        reset_num_timesteps=False,
    )
    model.save(model_out)
    env2.close()

    save_reward_curves(cb1.ep_rewards, cb1.ep_destructions, cb2.ep_rewards, cb2.ep_destructions, curve_out)
    print(f"Saved model -> {model_out} and reward curves -> {curve_out}", flush=True)
    return model_out, curve_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train MaskablePPO on CoCEnv.")
    parser.add_argument("--stage1-steps", type=int, default=20_000)
    parser.add_argument("--stage2-steps", type=int, default=60_000)
    parser.add_argument("--shaping", type=str, default="baseline")
    parser.add_argument("--model-out", type=Path, default=Path("models/ppo_coc_v1.zip"))
    parser.add_argument("--curve-out", type=Path, default=Path("results/reward_curves.png"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    train_pipeline(
        stage1_steps=args.stage1_steps,
        stage2_steps=args.stage2_steps,
        shaping_mode=args.shaping,
        model_out=args.model_out,
        curve_out=args.curve_out,
        seed=args.seed,
    )
