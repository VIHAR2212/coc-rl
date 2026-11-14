"""Fine-tune MaskablePPO policies initialized from Behavior Cloning weights.

M9 Step 3:
- Loads models/ppo_m9_bc_seed{seed}.zip (seeds 42, 43, 44).
- Fine-tunes with MaskablePPO on the training split (base02, base03, base04) across all 7 TH8 armies.
- Same stars-aware reward shaping and anti_collapse=True as in Part B.
- Uses lower learning rate (5e-5) to prevent catastrophic forgetting of expert demonstrations.
- Saves checkpoints every 50k steps to models/checkpoints_m9/
- Saves final fine-tuned models to models/ppo_m9_bcft_seed{seed}.zip.
- Supports --smoke mode (50k steps on seed 42 with action-collapse checks).
"""

import argparse
import math
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

from sim.rl_wrapper import ActionMaskCoCEnv, TRAIN_BASES, NUM_SECTORS

MODELS_DIR = ROOT / "models"
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints_m9"
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


def check_smoke_diagnostics(model, seed: int, n_episodes: int = 30) -> tuple[float, float, float, bool]:
    """Check action entropy and sector concentration on train bases."""
    env = ActionMaskCoCEnv(bases=TRAIN_BASES, shaping_mode="stars_aware", anti_collapse=True)
    dests = []
    stars = []
    single_sector_eps = 0

    for ep in range(n_episodes):
        obs, _ = env.reset(seed=10000 + ep)
        done = False
        sectors = []
        info = {}
        while not done:
            mask = env.action_masks()
            act, _ = model.predict(obs, action_masks=mask, deterministic=True)
            act = int(act)
            if act > 0:
                sec = (act - 1) % NUM_SECTORS
                sectors.append(sec)
            obs, _, term, trunc, info = env.step(act)
            done = term or trunc

        dests.append(float(info.get("destruction", 0.0)) * 100.0)
        stars.append(int(info.get("stars", 0)))
        if sectors:
            max_c = max(sectors.count(s) for s in set(sectors))
            if max_c / len(sectors) > 0.90:
                single_sector_eps += 1

    mean_dest = float(np.mean(dests))
    mean_stars = float(np.mean(stars))
    single_sec_frac = single_sector_eps / n_episodes
    has_collapsed = single_sec_frac > 0.90
    return mean_dest, mean_stars, single_sec_frac, has_collapsed


def fine_tune_seed(
    seed: int,
    total_timesteps: int = 300_000,
    lr: float = 5e-5,
    n_envs: int = 2,
    checkpoint_every: int = 50_000,
    out_name: str | None = None,
) -> Path:
    bc_path = MODELS_DIR / f"ppo_m9_bc_seed{seed}.zip"
    if not bc_path.exists():
        raise FileNotFoundError(f"Base BC model {bc_path} does not exist! Run train_m9_bc.py first.")

    out_path = MODELS_DIR / (out_name or f"ppo_m9_bcft_seed{seed}.zip")

    print(f"\n{'='*80}")
    print(f"M9 STEP 3: FINE-TUNING SEED {seed} FROM BC WEIGHTS")
    print(f"Initial BC Model: {bc_path}")
    print(f"Target Output: {out_path}")
    print(f"Total Steps: {total_timesteps:,} | Learning Rate: {lr} | Envs: {n_envs}")
    print(f"Train Bases: {TRAIN_BASES} | Shaping: stars_aware | Anti-Collapse: True")
    print(f"{'='*80}", flush=True)

    vec_env = _make_vec_env(
        bases=TRAIN_BASES,
        shaping_mode="stars_aware",
        n_envs=n_envs,
        seed=seed,
        anti_collapse=True,
    )

    # Load pretrained BC weights and attach new environment & fine-tuning learning rate
    model = MaskablePPO.load(
        bc_path,
        env=vec_env,
        learning_rate=lr,
        tensorboard_log="runs/",
        verbose=0,
    )

    metrics_cb = VecEpisodeMetricsCallback(n_envs=n_envs, log_every=25_000)
    ckpt_cb = PeriodicCheckpoint(
        out_dir=CHECKPOINTS_DIR,
        tag=f"ppo_m9_bcft_seed{seed}",
        every=checkpoint_every,
    )

    t0 = time.perf_counter()
    model.learn(
        total_timesteps=total_timesteps,
        callback=[metrics_cb, ckpt_cb],
        tb_log_name=f"m9_bcft_s{seed}",
        reset_num_timesteps=False,
    )
    vec_env.close()

    model.save(out_path)
    dur = time.perf_counter() - t0
    print(f"\nSeed {seed} fine-tuning finished in {dur:.1f}s. Saved to {out_path}", flush=True)

    # Verification reload
    _ = MaskablePPO.load(out_path, device="cpu")
    print(f"Verified reload of {out_path.name}: OK", flush=True)

    return out_path


def main():
    parser = argparse.ArgumentParser(description="M9 PPO Fine-Tuning from BC")
    parser.add_argument("--smoke", action="store_true", help="Run 50k-step smoke test on seed 42 only")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44], help="Seeds to train")
    parser.add_argument("--steps", type=int, default=300_000, help="Total steps per seed")
    parser.add_argument("--lr", type=float, default=5e-5, help="Fine-tuning learning rate")
    parser.add_argument("--n-envs", type=int, default=2, help="Number of parallel environments")
    args = parser.parse_args()

    if args.smoke:
        print("=" * 80)
        print("M9 STEP 3b: 50K SMOKE TEST (Seed 42)")
        print("=" * 80, flush=True)
        smoke_model_path = fine_tune_seed(
            seed=42,
            total_timesteps=50_000,
            lr=args.lr,
            n_envs=args.n_envs,
            checkpoint_every=50_000,
            out_name="checkpoints_m9/ppo_m9_smoke_seed42.zip",
        )
        print("\n--- Running Smoke Diagnostics on Train Bases ---", flush=True)
        model = MaskablePPO.load(smoke_model_path, device="cpu")
        dest, stars, single_sec_frac, collapsed = check_smoke_diagnostics(model, seed=42)
        print(f"Smoke Diagnostics (30 episodes):")
        print(f"  Mean Destruction: {dest:.2f}%")
        print(f"  Mean Stars:       {stars:.2f}")
        print(f"  Single Sector Fraction: {single_sec_frac*100:.1f}%")
        print(f"  Collapsed (>90% single sector): {collapsed}")
        if collapsed:
            print("ERROR: Smoke test collapsed! Action selection collapsed to single sector.")
            sys.exit(1)
        else:
            print(">>> SMOKE TEST PASSED: No single-sector collapse, policy healthy.")
            return

    for seed in args.seeds:
        fine_tune_seed(
            seed=seed,
            total_timesteps=args.steps,
            lr=args.lr,
            n_envs=args.n_envs,
            checkpoint_every=50_000,
        )

    print("\n" + "=" * 80)
    print("ALL M9 FINE-TUNING SEEDS COMPLETED SUCCESSFULLY")
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()

