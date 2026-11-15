"""Fine-tune MaskablePPO policies initialized from M10 Behavior Cloning weights.

M10 Step 1f:
- Loads models/ppo_m10_bc_seed{seed}.zip (seeds 42, 43, 44).
- Fine-tunes on the FULL train pool (300 layouts in data/bases_gen/train/) across all 7 TH8 armies.
- EXACTLY the M9 hyperparameters:
  * Learning rate: 5e-5
  * Entropy coefficient: 0.005
  * Reward shaping: stars_aware
  * Anti-collapse terms: True
  * Total steps: 300,000 per seed
  * Envs: 2 parallel SubprocVecEnv
- Benchmarks 1 layout before launching to print expected runtime.
- Saves checkpoints every 50k steps to models/checkpoints_m10/
- Saves final fine-tuned models to models/ppo_m10_bcft_seed{seed}.zip.
"""

import argparse
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.rl_wrapper import ActionMaskCoCEnv

DATA_DIR = ROOT / "data"
TRAIN_DIR = DATA_DIR / "bases_gen" / "train"
MODELS_DIR = ROOT / "models"
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints_m10"
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


def _mask_fn(env):
    return env.action_masks()


def make_masked_env(bases, shaping_mode="stars_aware", rank=0, seed=42, anti_collapse=True):
    env = ActionMaskCoCEnv(bases=bases, shaping_mode=shaping_mode, anti_collapse=anti_collapse)
    env = ActionMasker(env, _mask_fn)
    env.reset(seed=seed + rank)
    return Monitor(env)


def _make_vec_env(bases, shaping_mode: str, n_envs: int, seed: int, anti_collapse: bool = True):
    fns = [partial(make_masked_env, bases, shaping_mode, rank, seed, anti_collapse) for rank in range(n_envs)]
    return DummyVecEnv(fns) if n_envs == 1 else SubprocVecEnv(fns)


class PeriodicCheckpoint(BaseCallback):
    """Save a checkpoint every `every` training steps."""

    def __init__(self, out_dir: Path, tag: str, every: int = 50_000, verbose: int = 0):
        super().__init__(verbose)
        self.out_dir = out_dir
        self.tag = tag
        self.every = every
        self._next = 0
        self.saved: list[Path] = []

    def _on_step(self) -> bool:
        while self.num_timesteps >= self._next + self.every:
            self._next += self.every
            path = self.out_dir / f"{self.tag}_step{self._next // 1000:03d}k.zip"
            self.model.save(path)
            self.saved.append(path)
            print(f"  [Checkpoint] Saved {path.name} at step {self.num_timesteps:,}", flush=True)
        return True


class VecEpisodeMetricsCallback(BaseCallback):
    """Collect per-episode reward, destruction %, and stars across vectorized envs."""

    def __init__(self, n_envs: int, log_every: int = 25_000):
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
            recent_d = float(np.mean(self.ep_destructions[-100:]))
            recent_s = float(np.mean(self.ep_stars[-100:]))
            recent_r = float(np.mean(self.ep_rewards[-100:]))
            print(
                f"  step={self.num_timesteps:,} | episodes={len(self.ep_destructions)} "
                f"| recent-100: dest={recent_d:5.1f}% stars={recent_s:4.2f} rew={recent_r:6.2f}",
                flush=True,
            )
            while self._next_log <= self.num_timesteps:
                self._next_log += self.log_every
        return True


def benchmark_1_layout(benchmark_steps: int = 2_000) -> float:
    """Run a quick benchmark on a single layout to estimate throughput."""
    single_base = sorted(TRAIN_DIR.glob("gen_base_*.json"))[0]
    vec_env = _make_vec_env(bases=str(single_base), shaping_mode="stars_aware", n_envs=2, seed=999)
    # Temporary mock model
    from sim.rl_wrapper import CoCFeatureExtractor
    model = MaskablePPO(
        "MultiInputPolicy",
        vec_env,
        learning_rate=5e-5,
        policy_kwargs=dict(
            features_extractor_class=CoCFeatureExtractor,
            features_extractor_kwargs=dict(features_dim=128),
            net_arch=dict(pi=[128, 64], vf=[128, 64]),
        ),
        verbose=0,
    )
    t0 = time.perf_counter()
    model.learn(total_timesteps=benchmark_steps)
    dur = time.perf_counter() - t0
    vec_env.close()

    sps = benchmark_steps / dur
    print(f"Benchmark: {benchmark_steps} steps in {dur:.2f}s ({sps:.1f} steps/s)")
    return sps


def fine_tune_seed(
    seed: int,
    total_timesteps: int = 300_000,
    lr: float = 5e-5,
    ent_coef: float = 0.005,
    n_envs: int = 2,
    checkpoint_every: int = 50_000,
) -> Path:
    bc_path = MODELS_DIR / f"ppo_m10_bc_seed{seed}.zip"
    if not bc_path.exists():
        raise FileNotFoundError(f"Base BC model {bc_path} does not exist! Run train_m10_bc.py first.")

    out_path = MODELS_DIR / f"ppo_m10_bcft_seed{seed}.zip"

    print(f"\n{'='*80}")
    print(f"M10 STEP 1f: FINE-TUNING SEED {seed} FROM BC WEIGHTS")
    print(f"Initial BC Model: {bc_path}")
    print(f"Target Output: {out_path}")
    print(f"Total Steps: {total_timesteps:,} | Learning Rate: {lr} | Ent Coef: {ent_coef} | Envs: {n_envs}")
    print(f"Train Pool: 300 layouts in {TRAIN_DIR.name} | Shaping: stars_aware | Anti-Collapse: True")
    print(f"{'='*80}", flush=True)

    vec_env = _make_vec_env(
        bases=str(TRAIN_DIR),
        shaping_mode="stars_aware",
        n_envs=n_envs,
        seed=seed,
        anti_collapse=True,
    )

    # Load pretrained BC weights and attach new environment & fine-tuning hyperparameters
    model = MaskablePPO.load(
        bc_path,
        env=vec_env,
        learning_rate=lr,
        ent_coef=ent_coef,
        tensorboard_log="runs/",
        verbose=0,
    )

    metrics_cb = VecEpisodeMetricsCallback(n_envs=n_envs, log_every=25_000)
    ckpt_cb = PeriodicCheckpoint(
        out_dir=CHECKPOINTS_DIR,
        tag=f"ppo_m10_bcft_seed{seed}",
        every=checkpoint_every,
    )

    t0 = time.perf_counter()
    model.learn(
        total_timesteps=total_timesteps,
        callback=[metrics_cb, ckpt_cb],
        tb_log_name=f"m10_bcft_s{seed}",
        reset_num_timesteps=False,
    )
    vec_env.close()

    model.save(out_path)
    dur = time.perf_counter() - t0
    print(f"\nSeed {seed} fine-tuning finished in {dur:.1f}s ({dur/60:.1f} min). Saved to {out_path}", flush=True)

    # Verification reload
    _ = MaskablePPO.load(out_path, device="cpu")
    print(f"Verified reload of {out_path.name}: OK", flush=True)

    return out_path


def main():
    parser = argparse.ArgumentParser(description="M10 PPO Fine-Tuning on 300 Layouts")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44], help="Seeds to train")
    parser.add_argument("--steps", type=int, default=300_000, help="Total steps per seed")
    parser.add_argument("--lr", type=float, default=5e-5, help="Fine-tuning learning rate")
    parser.add_argument("--ent-coef", type=float, default=0.005, help="Entropy coefficient")
    parser.add_argument("--n-envs", type=int, default=2, help="Parallel envs")
    args = parser.parse_args()

    print("=" * 80)
    print("M10 STEP 1f: PRE-LAUNCH BENCHMARK ON 1 LAYOUT")
    print("=" * 80, flush=True)

    sps = benchmark_1_layout(benchmark_steps=1_500)
    expected_sec_per_seed = args.steps / max(1.0, sps)
    total_expected_hours = (expected_sec_per_seed * len(args.seeds)) / 3600.0

    print(f"\nExpected Runtime Projection:")
    print(f"  Throughput:                 {sps:.1f} steps/s")
    print(f"  Per Seed ({args.steps:,} steps): {expected_sec_per_seed/60:.1f} minutes ({expected_sec_per_seed/3600:.2f} hours)")
    print(f"  Total ({len(args.seeds)} seeds):        {total_expected_hours:.2f} hours")
    print("=" * 80, flush=True)

    for seed in args.seeds:
        fine_tune_seed(
            seed=seed,
            total_timesteps=args.steps,
            lr=args.lr,
            ent_coef=args.ent_coef,
            n_envs=args.n_envs,
            checkpoint_every=50_000,
        )

    print("\n" + "=" * 80)
    print("ALL M10 FINE-TUNING SEEDS COMPLETED SUCCESSFULLY")
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
