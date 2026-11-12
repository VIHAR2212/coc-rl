"""Record PNG frames and animated GIFs of baseline and trained PPO attacks to docs/."""

import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.rule_based import rule_based_action
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv

DOCS_DIR = ROOT / "docs"


def record_demo(base_file="base03.json", army="giant_barch", seed=0, sample_every=15, duration=250):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    env = CoCEnv(base_file=base_file, army=army, render_mode="rgb_array")
    env.reset(seed=seed)

    gif_frames = []
    saved_pngs = []
    step_idx = 0
    done = False
    info = {}

    while not done:
        frame = env.render()
        img = Image.fromarray(frame)
        if step_idx % 2 == 0:
            gif_frames.append(img)
        if step_idx % sample_every == 0:
            png_path = DOCS_DIR / f"frame_{step_idx:03d}.png"
            img.save(png_path)
            saved_pngs.append(png_path)
        _, _, term, trunc, info = env.step(rule_based_action(env, step_idx))
        done = term or trunc
        step_idx += 1

    final_img = Image.fromarray(env.render())
    gif_frames.append(final_img)
    final_png = DOCS_DIR / f"frame_{step_idx:03d}.png"
    final_img.save(final_png)
    saved_pngs.append(final_png)

    gif_path = DOCS_DIR / "baseline_attack.gif"
    gif_frames[0].save(
        gif_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=duration,
        loop=0,
    )
    env.close()
    print(
        f"Saved {len(saved_pngs)} PNG frames and {gif_path.name} ({len(gif_frames)} gif frames, duration={duration}ms) "
        f"| dest={info['destruction']*100:.1f}% stars={info['stars']}"
    )
    return saved_pngs, gif_path


def record_rl_demo(
    base_file="base06.json",
    army="giant_barch",
    model_path=None,
    seed=0,
    duration=250,
):
    from sb3_contrib import MaskablePPO

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if model_path is None:
        candidates = sorted(Path("models").glob("ppo_m7b_seed*.zip"))
        model_path = candidates[0] if candidates else Path("models/ppo_coc_v1.zip")

    model = MaskablePPO.load(model_path, device="cpu")
    env = ActionMaskCoCEnv(bases=[base_file], armies=[army], render_mode="rgb_array")
    obs, _ = env.reset(seed=seed, options={"base_file": base_file, "army": army})

    gif_frames = []
    step_idx = 0
    done = False
    info = {}

    while not done:
        frame = env.render()
        if step_idx % 2 == 0:
            gif_frames.append(Image.fromarray(frame))
        mask = env.action_masks()
        action, _ = model.predict(obs, deterministic=True, action_masks=mask)
        obs, _, term, trunc, info = env.step(int(action))
        done = term or trunc
        step_idx += 1

    gif_frames.append(Image.fromarray(env.render()))
    gif_path = DOCS_DIR / "ppo_attack.gif"
    gif_frames[0].save(
        gif_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=duration,
        loop=0,
    )
    env.close()
    print(
        f"Saved {gif_path.name} ({len(gif_frames)} gif frames, duration={duration}ms) "
        f"| model={model_path.name} base={base_file} dest={info['destruction']*100:.1f}% stars={info['stars']}"
    )
    return gif_path


if __name__ == "__main__":
    record_demo()
    record_rl_demo()
