"""Multi-seed MaskablePPO training (Stage 1 single base -> Stage 2 train split, TensorBoard + curves)."""
import argparse
import time
from functools import partial
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

from sim.rl_wrapper import ActionMaskCoCEnv, CoCFeatureExtractor, TRAIN_BASES


def _mask_fn(env):
    return env.action_masks()


def make_masked_env(bases, shaping_mode="stars_aware", rank=0, seed=42):
    env = ActionMaskCoCEnv(bases=bases, shaping_mode=shaping_mode)
    env = ActionMasker(env, _mask_fn)
    env.reset(seed=seed + rank)
    return Monitor(env)


class VecEpisodeMetricsCallback(BaseCallback):
    """Collect per-episode reward, destruction %, and stars across vectorized envs."""

    def __init__(self, n_envs: int, log_every: int = 50_000):
        super().__init__()
        self.ep_rewards: list[float] = []
        self.ep_destructions: list[float] = []
        self.ep_stars: list[int] = []
        self._running = [0.0] * n_envs
        self.log_every = log_every
        self._next_log = log_every

    def _on_step(self) -> bool:
        rewards = self.locals.get("rewards", [])
        dones = self.locals.get("dones", [])
        infos = self.locals.get("infos", [])
        for i in range(len(dones)):
            self._running[i] += float(rewards[i])
            if dones[i]:
                self.ep_rewards.append(self._running[i])
                self.ep_destructions.append(float(infos[i].get("destruction", 0.0)) * 100.0)
                self.ep_stars.append(int(infos[i].get("stars", 0)))
                self._running[i] = 0.0
        if self.num_timesteps >= self._next_log and self.ep_destructions:
            print(
                f"  step={self.num_timesteps:,} | episodes={len(self.ep_destructions)} "
                f"| recent-100 dest={np.mean(self.ep_destructions[-100:]):.1f}% "
                f"stars={np.mean(self.ep_stars[-100:]):.2f}",
                flush=True,
            )
            while self._next_log <= self.num_timesteps:
                self._next_log += self.log_every
        return True


def _rolling(vals: list[float], window: int = 40) -> np.ndarray:
    if not vals:
        return np.array([], dtype=np.float32)
    arr = np.asarray(vals, dtype=np.float32)
    csum = np.cumsum(np.insert(arr, 0, 0.0))
    out = np.empty_like(arr)
    for i in range(len(arr)):
        lo = max(0, i - window + 1)
        out[i] = float((csum[i + 1] - csum[lo]) / (i - lo + 1))
    return out


def save_multi_seed_curves(seed_logs: dict[int, dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    specs = [
        (axes[0, 0], "s1_rew", "Stage 1 (base03): Episode Reward", "Reward"),
        (axes[0, 1], "s1_dest", "Stage 1 (base03): Destruction %", "Destruction (%)"),
        (axes[1, 0], "s2_rew", "Stage 2 (base02..04, 500k): Episode Reward", "Reward"),
        (axes[1, 1], "s2_dest", "Stage 2 (base02..04, 500k): Destruction %", "Destruction (%)"),
    ]
    for ax, key, title, ylabel in specs:
        for seed, log in sorted(seed_logs.items()):
            vals = log[key]
            if vals:
                win = max(10, len(vals) // 40)
                ax.plot(np.arange(1, len(vals) + 1), _rolling(vals, win), linewidth=1.6, label=f"seed {seed}")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("Episode")
        ax.set_ylabel(ylabel)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def _make_vec_env(bases, shaping_mode: str, n_envs: int, seed: int):
    fns = [partial(make_masked_env, bases, shaping_mode, rank, seed) for rank in range(n_envs)]
    return DummyVecEnv(fns) if n_envs == 1 else SubprocVecEnv(fns)


def train_single_seed(
    seed: int,
    single_base: str,
    train_bases: list[str],
    stage1_steps: int,
    stage2_steps: int,
    n_envs: int,
    shaping_mode: str,
    models_dir: Path,
) -> tuple[Path, dict]:
    policy_kwargs = dict(
        features_extractor_class=CoCFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=128),
        net_arch=dict(pi=[128, 64], vf=[128, 64]),
    )
    t0 = time.perf_counter()
    print(f"\n=== Seed {seed} | Stage 1: {single_base} ({stage1_steps} steps, n_envs={n_envs}) ===", flush=True)
    env1 = _make_vec_env([single_base], shaping_mode, n_envs, seed)
    cb1 = VecEpisodeMetricsCallback(n_envs, log_every=25_000)
    n_steps = max(256, 4096 // n_envs)
    model = MaskablePPO(
        "MultiInputPolicy",
        env1,
        learning_rate=3e-4,
        n_steps=n_steps,
        batch_size=512,
        n_epochs=3,
        gamma=0.99,
        ent_coef=0.015,
        policy_kwargs=policy_kwargs,
        tensorboard_log="runs/",
        seed=seed,
        verbose=0,
    )
    model.learn(total_timesteps=stage1_steps, callback=cb1, tb_log_name=f"m7b_s{seed}_stage1")
    env1.close()
    print(
        f"Seed {seed} Stage 1 done in {time.perf_counter() - t0:.1f}s "
        f"| last-50 dest={np.mean(cb1.ep_destructions[-50:]):.1f}%",
        flush=True,
    )

    t1 = time.perf_counter()
    print(f"=== Seed {seed} | Stage 2: {train_bases} ({stage2_steps} steps) ===", flush=True)
    env2 = _make_vec_env(train_bases, shaping_mode, n_envs, seed + 100)
    cb2 = VecEpisodeMetricsCallback(n_envs, log_every=100_000)
    model.set_env(env2)
    model.learn(
        total_timesteps=stage2_steps,
        callback=cb2,
        tb_log_name=f"m7b_s{seed}_stage2",
        reset_num_timesteps=False,
    )
    env2.close()

    out_path = models_dir / f"ppo_m7b_seed{seed}.zip"
    model.save(out_path)
    print(
        f"Seed {seed} Stage 2 done in {time.perf_counter() - t1:.1f}s "
        f"| last-100 dest={np.mean(cb2.ep_destructions[-100:]):.1f}% stars={np.mean(cb2.ep_stars[-100:]):.2f} "
        f"| saved {out_path}",
        flush=True,
    )
    return out_path, {
        "s1_rew": cb1.ep_rewards,
        "s1_dest": cb1.ep_destructions,
        "s2_rew": cb2.ep_rewards,
        "s2_dest": cb2.ep_destructions,
    }


def train_pipeline(
    single_base: str = "base03.json",
    train_bases: list[str] | None = None,
    stage1_steps: int = 25_000,
    stage2_steps: int = 500_000,
    seeds: list[int] | None = None,
    n_envs: int = 4,
    shaping_mode: str = "stars_aware",
    models_dir: Path = Path("models"),
    curve_out: Path = Path("results/reward_curves.png"),
):
    train_bases = train_bases or list(TRAIN_BASES)
    seeds = seeds or [42, 43, 44]
    models_dir.mkdir(parents=True, exist_ok=True)
    seed_logs: dict[int, dict] = {}
    saved_models: list[Path] = []
    for s in seeds:
        path, log = train_single_seed(
            seed=s,
            single_base=single_base,
            train_bases=train_bases,
            stage1_steps=stage1_steps,
            stage2_steps=stage2_steps,
            n_envs=n_envs,
            shaping_mode=shaping_mode,
            models_dir=models_dir,
        )
        saved_models.append(path)
        seed_logs[s] = log
    save_multi_seed_curves(seed_logs, curve_out)
    print(f"\nSaved {len(saved_models)} models and multi-seed reward curves -> {curve_out}", flush=True)
    return saved_models, curve_out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-seed MaskablePPO training for M7b.")
    parser.add_argument("--stage1-steps", type=int, default=25_000)
    parser.add_argument("--stage2-steps", type=int, default=500_000)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--shaping", type=str, default="stars_aware")
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--curve-out", type=Path, default=Path("results/reward_curves.png"))
    args = parser.parse_args()
    train_pipeline(
        stage1_steps=args.stage1_steps,
        stage2_steps=args.stage2_steps,
        seeds=args.seeds,
        n_envs=args.n_envs,
        shaping_mode=args.shaping,
        models_dir=args.models_dir,
        curve_out=args.curve_out,
    )
