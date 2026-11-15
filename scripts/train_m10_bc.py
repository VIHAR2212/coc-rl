"""M10 Step 1e: Behavior Cloning (BC) on 100-Layout Expert Demonstrations.

1. Layout-Split Validation:
   Splits demonstrations by layout (80 train layouts, 20 val layouts).
   Trains supervised masked cross-entropy and evaluates validation accuracy and non-wait action accuracy.
2. Full Retraining:
   Trains across all 100 demonstration layouts for seeds 42, 43, 44.
   Saves models to models/ppo_m10_bc_seed{42,43,44}.zip.
"""

import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from sb3_contrib import MaskablePPO
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.rl_wrapper import ActionMaskCoCEnv, CoCFeatureExtractor

DATA_DIR = ROOT / "data"
DEMOS_PATH = DATA_DIR / "demos" / "m10_train_demos.npz"
TRAIN_DIR = DATA_DIR / "bases_gen" / "train"
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
    """Create a MaskablePPO model using the train pool."""
    env = ActionMaskCoCEnv(bases=str(TRAIN_DIR), shaping_mode="stars_aware", anti_collapse=True)
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

        masked_logits = torch.where(mask, logits, torch.tensor(huge_neg, device=device, dtype=logits.dtype))
        loss = F.cross_entropy(masked_logits, act)
        loss.backward()
        optimizer.step()

        pred = torch.argmax(masked_logits, dim=-1)
        acc = (pred == act).float().mean()

        non_wait = act > 0
        acc_nw = (pred[non_wait] == act[non_wait]).float().mean() if non_wait.any() else torch.tensor(1.0, device=device)

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
        acc_nw = (pred[non_wait] == act[non_wait]).float().mean() if non_wait.any() else torch.tensor(1.0, device=device)

        total_loss += loss.item()
        total_acc += acc.item()
        total_acc_nw += acc_nw.item()
        n_batches += 1

    return total_loss / n_batches, total_acc / n_batches, total_acc_nw / n_batches


def layout_split_validation(data: dict, batch_size: int = 512, epochs: int = 10, lr: float = 1e-3):
    print("=" * 80)
    print("M10 STEP 1e: LAYOUT-SPLIT VALIDATION (80 Train Layouts / 20 Val Layouts)")
    print("=" * 80, flush=True)

    layout_ids = data["layout_ids"]
    # 80 train layouts (0..79), 20 val layouts (80..99)
    train_idx = np.where(layout_ids < 80)[0]
    val_idx = np.where(layout_ids >= 80)[0]

    train_ds = BCDataset(data["grids"][train_idx], data["armies"][train_idx], data["masks"][train_idx], data["actions"][train_idx])
    val_ds = BCDataset(data["grids"][val_idx], data["armies"][val_idx], data["masks"][val_idx], data["actions"][val_idx])

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    print(f"Train samples: {len(train_ds):,} | Val samples: {len(val_ds):,}")

    model = make_bc_model(seed=42)
    device = "cpu"
    optimizer = torch.optim.Adam(model.policy.parameters(), lr=lr)

    for epoch in range(1, epochs + 1):
        t0 = time.perf_counter()
        tr_loss, tr_acc, tr_acc_nw = train_epoch(model, train_loader, optimizer, device)
        val_loss, val_acc, val_acc_nw = evaluate_dataset(model, val_loader, device)
        dur = time.perf_counter() - t0
        print(
            f"  Epoch {epoch:2d}/{epochs:2d} ({dur:4.1f}s) | "
            f"Train: loss={tr_loss:.4f} acc={tr_acc*100:.1f}% (nw={tr_acc_nw*100:.1f}%) | "
            f"Val: loss={val_loss:.4f} acc={val_acc*100:.1f}% (nw={val_acc_nw*100:.1f}%)",
            flush=True,
        )

    print(f"\nFinal Validation on 20 Held-Out Layouts: Acc = {val_acc*100:.2f}%, Non-Wait Acc = {val_acc_nw*100:.2f}%\n")


def full_retrain_and_save(data: dict, seeds: list[int] = [42, 43, 44], batch_size: int = 512, epochs: int = 12, lr: float = 1e-3):
    print("=" * 80)
    print(f"M10 STEP 1e: FULL RETRAINING ON ALL 100 LAYOUTS (Seeds {seeds})")
    print("=" * 80, flush=True)

    dataset = BCDataset(data["grids"], data["armies"], data["masks"], data["actions"])
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    device = "cpu"

    for seed in seeds:
        print(f"\n--- Retraining Seed {seed} ({len(dataset):,} transitions) ---")
        model = make_bc_model(seed=seed, device=device)
        optimizer = torch.optim.Adam(model.policy.parameters(), lr=lr)

        t0 = time.perf_counter()
        for epoch in range(1, epochs + 1):
            loss, acc, acc_nw = train_epoch(model, loader, optimizer, device)
            if epoch % 3 == 0 or epoch == epochs:
                print(f"  Epoch {epoch:2d}/{epochs:2d}: loss={loss:.4f} acc={acc*100:.1f}% non_wait_acc={acc_nw*100:.1f}%", flush=True)

        dur = time.perf_counter() - t0
        out_path = MODELS_DIR / f"ppo_m10_bc_seed{seed}.zip"
        model.save(out_path)
        print(f"Seed {seed} finished in {dur:.1f}s. Saved to {out_path.name}")

        # Verification reload
        _ = MaskablePPO.load(out_path, device="cpu")
        print(f"Verified reload of {out_path.name}: OK", flush=True)


def main():
    if not DEMOS_PATH.exists():
        raise FileNotFoundError(f"Demonstrations file {DEMOS_PATH} not found! Run record_m10_demos.py first.")

    print(f"Loading demonstrations from {DEMOS_PATH.name}...")
    npz = np.load(DEMOS_PATH)
    data = {k: npz[k] for k in npz.files}
    print(f"Loaded {len(data['actions']):,} transitions across {len(set(data['layout_ids']))} layouts and {len(set(data['army_ids']))} armies.\n")

    layout_split_validation(data, batch_size=512, epochs=8, lr=1e-3)
    full_retrain_and_save(data, seeds=[42, 43, 44], batch_size=512, epochs=10, lr=1e-3)


if __name__ == "__main__":
    main()
