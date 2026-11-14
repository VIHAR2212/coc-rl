"""Behavior Cloning (BC) on Left Wave expert demonstrations.

M9 Step 2a & 2b:
- 2a: Split train/val by base (leave-one-base-out cross validation).
      Report validation accuracy and non-wait action accuracy.
- 2b: Retrain on all three bases across seeds 42, 43, 44.
      Save models to models/ppo_m9_bc_seed{42,43,44}.zip.
"""

import sys
import time
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from sb3_contrib import MaskablePPO

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.rl_wrapper import ActionMaskCoCEnv, CoCFeatureExtractor, TRAIN_BASES

DATA_DIR = ROOT / "data"
DEMOS_PATH = DATA_DIR / "demos" / "left_wave_train_demos.npz"
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


class BCDataset(Dataset):
    def __init__(self, grids, armies, masks, actions):
        self.grids = torch.from_numpy(grids)
        self.armies = torch.from_numpy(armies)
        self.masks = torch.from_numpy(masks)
        self.actions = torch.from_numpy(actions).long()

    def __len__(self):
        return len(self.actions)

    def __getitem__(self, idx):
        return {
            "grid": self.grids[idx],
            "army": self.armies[idx],
        }, self.masks[idx], self.actions[idx]


def make_bc_model(seed: int, device: str = "cpu") -> MaskablePPO:
    """Create a MaskablePPO model with identical architecture as Part B."""
    env = ActionMaskCoCEnv(bases=TRAIN_BASES, shaping_mode="stars_aware", anti_collapse=True)
    policy_kwargs = dict(
        features_extractor_class=CoCFeatureExtractor,
        features_extractor_kwargs=dict(features_dim=128),
        net_arch=dict(pi=[128, 64], vf=[128, 64]),
    )
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        learning_rate=3e-4,
        policy_kwargs=policy_kwargs,
        seed=seed,
        device=device,
        verbose=0,
    )
    env.close()
    return model


def train_epoch(model, dataloader, optimizer, device) -> tuple[float, float, float]:
    model.policy.train()
    total_loss = 0.0
    total_acc = 0.0
    total_acc_nw = 0.0
    n_batches = 0
    huge_neg = -1e8

    for obs_batch, mask_batch, act_batch in dataloader:
        obs = {k: v.to(device) for k, v in obs_batch.items()}
        mask = mask_batch.to(device)
        act = act_batch.to(device)

        optimizer.zero_grad()
        features = model.policy.extract_features(obs)
        latent_pi, _ = model.policy.mlp_extractor(features)
        logits = model.policy.action_net(latent_pi)

        # Mask invalid actions
        masked_logits = torch.where(mask, logits, torch.tensor(huge_neg, device=device, dtype=logits.dtype))
        loss = F.cross_entropy(masked_logits, act)
        loss.backward()
        optimizer.step()

        pred = torch.argmax(masked_logits, dim=-1)
        acc = (pred == act).float().mean()

        non_wait = act > 0
        if non_wait.any():
            acc_nw = (pred[non_wait] == act[non_wait]).float().mean()
        else:
            acc_nw = torch.tensor(1.0, device=device)

        total_loss += loss.item()
        total_acc += acc.item()
        total_acc_nw += acc_nw.item()
        n_batches += 1

    return total_loss / n_batches, total_acc / n_batches, total_acc_nw / n_batches


@torch.no_grad()
def evaluate_dataset(model, dataloader, device) -> tuple[float, float, float]:
    model.policy.eval()
    total_loss = 0.0
    total_acc = 0.0
    total_acc_nw = 0.0
    n_batches = 0
    huge_neg = -1e8

    for obs_batch, mask_batch, act_batch in dataloader:
        obs = {k: v.to(device) for k, v in obs_batch.items()}
        mask = mask_batch.to(device)
        act = act_batch.to(device)

        features = model.policy.extract_features(obs)
        latent_pi, _ = model.policy.mlp_extractor(features)
        logits = model.policy.action_net(latent_pi)

        masked_logits = torch.where(mask, logits, torch.tensor(huge_neg, device=device, dtype=logits.dtype))
        loss = F.cross_entropy(masked_logits, act)

        pred = torch.argmax(masked_logits, dim=-1)
        acc = (pred == act).float().mean()

        non_wait = act > 0
        if non_wait.any():
            acc_nw = (pred[non_wait] == act[non_wait]).float().mean()
        else:
            acc_nw = torch.tensor(1.0, device=device)

        total_loss += loss.item()
        total_acc += acc.item()
        total_acc_nw += acc_nw.item()
        n_batches += 1

    return total_loss / n_batches, total_acc / n_batches, total_acc_nw / n_batches


def step_2a_cross_validation(data: dict, batch_size: int = 512, epochs: int = 10, lr: float = 1e-3):
    print("=" * 80)
    print("M9 STEP 2a: BY-BASE CROSS VALIDATION")
    print("=" * 80)

    grids = data["grids"]
    armies = data["armies"]
    masks = data["masks"]
    actions = data["actions"]
    base_ids = data["base_ids"]
    bases = [str(b) for b in data["bases"]]

    cv_results = []

    for val_idx, val_base in enumerate(bases):
        print(f"\n--- Split {val_idx + 1}/3: Validate on {val_base} (Train on others) ---")
        train_mask = base_ids != val_idx
        val_mask = base_ids == val_idx

        train_ds = BCDataset(grids[train_mask], armies[train_mask], masks[train_mask], actions[train_mask])
        val_ds = BCDataset(grids[val_mask], armies[val_mask], masks[val_mask], actions[val_mask])

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

        model = make_bc_model(seed=42)
        optimizer = torch.optim.Adam(model.policy.parameters(), lr=lr)
        device = model.device

        for epoch in range(1, epochs + 1):
            t_start = time.perf_counter()
            tr_loss, tr_acc, tr_nw = train_epoch(model, train_loader, optimizer, device)
            val_loss, val_acc, val_nw = evaluate_dataset(model, val_loader, device)
            dur = time.perf_counter() - t_start
            if epoch in (1, epochs // 2, epochs):
                print(
                    f"  Epoch {epoch:2d}/{epochs:2d} ({dur:.1f}s) | "
                    f"Train Loss: {tr_loss:.4f}, Acc: {tr_acc*100:5.1f}%, Non-wait Acc: {tr_nw*100:5.1f}% | "
                    f"Val Loss: {val_loss:.4f}, Acc: {val_acc*100:5.1f}%, Non-wait Acc: {val_nw*100:5.1f}%",
                    flush=True,
                )

        cv_results.append({
            "val_base": val_base,
            "val_acc": val_acc,
            "val_nw_acc": val_nw,
        })

    print("\n" + "=" * 80)
    print("STEP 2a CROSS-VALIDATION SUMMARY:")
    for res in cv_results:
        print(f"  Hold-out {res['val_base']:<12}: Val Acc = {res['val_acc']*100:.2f}%, Non-wait Acc = {res['val_nw_acc']*100:.2f}%")
    mean_acc = np.mean([r["val_acc"] for r in cv_results]) * 100
    mean_nw = np.mean([r["val_nw_acc"] for r in cv_results]) * 100
    print(f"  Mean across splits: Val Acc = {mean_acc:.2f}%, Non-wait Acc = {mean_nw:.2f}%")
    print("=" * 80, flush=True)


def step_2b_full_train(data: dict, seeds: tuple[int, ...] = (42, 43, 44), batch_size: int = 512, epochs: int = 15, lr: float = 1e-3):
    print("\n" + "=" * 80)
    print(f"M9 STEP 2b: FULL BEHAVIOR CLONING ON ALL 3 BASES (SEEDS {seeds})")
    print("=" * 80)

    grids = data["grids"]
    armies = data["armies"]
    masks = data["masks"]
    actions = data["actions"]

    dataset = BCDataset(grids, armies, masks, actions)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    for seed in seeds:
        print(f"\n--- Training Seed {seed} ---", flush=True)
        torch.manual_seed(seed)
        np.random.seed(seed)

        model = make_bc_model(seed=seed)
        optimizer = torch.optim.Adam(model.policy.parameters(), lr=lr)
        device = model.device

        t0 = time.perf_counter()
        for epoch in range(1, epochs + 1):
            loss, acc, nw = train_epoch(model, loader, optimizer, device)
            if epoch in (1, 5, 10, epochs):
                print(f"  Epoch {epoch:2d}/{epochs:2d} | Loss: {loss:.4f} | Acc: {acc*100:5.2f}% | Non-wait Acc: {nw*100:5.2f}%", flush=True)

        out_model_path = MODELS_DIR / f"ppo_m9_bc_seed{seed}.zip"
        model.save(out_model_path)
        dur = time.perf_counter() - t0
        print(f"Saved BC model for seed {seed} to {out_model_path} in {dur:.1f}s", flush=True)

        # Verification reload
        _ = MaskablePPO.load(out_model_path, device="cpu")
        print(f"Verified reload of {out_model_path.name}: OK", flush=True)

    print("\n>>> STEP 2b FULL TRAINING: PASSED")


def main():
    if not DEMOS_PATH.exists():
        print(f"Error: {DEMOS_PATH} not found. Run scripts/record_m9_demos.py first.")
        sys.exit(1)

    print(f"Loading demonstrations from {DEMOS_PATH} ...", end="", flush=True)
    t0 = time.perf_counter()
    data = np.load(DEMOS_PATH)
    print(f" Done ({data['actions'].shape[0]:,} steps loaded in {time.perf_counter() - t0:.1f}s)")

    # 2a. By-base cross validation
    step_2a_cross_validation(data, batch_size=512, epochs=10, lr=1e-3)

    # 2b. Retrain on all three bases
    step_2b_full_train(data, seeds=(42, 43, 44), batch_size=512, epochs=15, lr=1e-3)


if __name__ == "__main__":
    main()

