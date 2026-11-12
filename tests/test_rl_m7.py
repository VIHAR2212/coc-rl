"""Tests for M7 MaskablePPO wrapper, action masking, and pipeline compatibility."""
import numpy as np
from sb3_contrib.common.wrappers import ActionMasker
from stable_baselines3.common.env_checker import check_env

from sim.rl_wrapper import ActionMaskCoCEnv


def test_action_mask_wrapper_valid_gymnasium():
    env = ActionMaskCoCEnv(bases=["base04.json"], armies=["mixed_wb"])
    check_env(env, warn=False)
    wrapped = ActionMasker(env, lambda e: e.action_masks())
    check_env(wrapped, warn=False)


def test_action_mask_blocks_wait_at_start_and_depleted_troops():
    env = ActionMaskCoCEnv(bases=["base05.json"], armies=["barch"])
    env.reset(seed=0)
    mask0 = env.action_masks()
    # Wait is blocked on step 0 while army is full and no troops are on field.
    assert not mask0[0]
    assert np.any(mask0[1:])

    # Drain all troops in army_left and verify all deploy actions become masked out.
    for k in env.troop_keys:
        env.env.army_left[k] = 0
    mask_empty = env.action_masks()
    assert mask_empty[0]
    assert not np.any(mask_empty[1:])


def test_maskable_ppo_smoke_learn_and_predict():
    from sb3_contrib import MaskablePPO
    from sim.rl_wrapper import CoCFeatureExtractor

    env = ActionMasker(ActionMaskCoCEnv(bases=["base01.json"], armies=["giant_barch"]), lambda e: e.action_masks())
    model = MaskablePPO(
        "MultiInputPolicy",
        env,
        n_steps=64,
        batch_size=32,
        n_epochs=1,
        policy_kwargs=dict(
            features_extractor_class=CoCFeatureExtractor,
            features_extractor_kwargs=dict(features_dim=160),
            net_arch=dict(pi=[32], vf=[32]),
        ),
        seed=0,
        verbose=0,
    )
    model.learn(total_timesteps=64)
    obs, _ = env.reset(seed=0)
    mask = env.env.action_masks()
    action, _ = model.predict(obs, deterministic=True, action_masks=mask)
    assert mask[int(action)]


