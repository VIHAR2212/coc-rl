"""Record PNG frames and an animated GIF of one rule-based baseline attack to docs/."""

import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.rule_based import rule_based_action
from sim import CoCEnv

DOCS_DIR = ROOT / "docs"


def record_demo(base_file="base03.json", army="giant_barch", seed=0, sample_every=15):
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
        duration=120,
        loop=0,
    )
    env.close()
    print(
        f"Saved {len(saved_pngs)} PNG frames and {gif_path.name} ({len(gif_frames)} gif frames) "
        f"| dest={info['destruction']*100:.1f}% stars={info['stars']}"
    )
    return saved_pngs, gif_path


if __name__ == "__main__":
    record_demo()
