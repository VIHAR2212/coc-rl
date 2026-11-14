"""Record side-by-side battle GIFs comparing Left Wave vs MaskablePPO across held-out bases."""

import argparse
import csv
import math
import shutil
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.rule_based import rule_based_action
from sim import CoCEnv
from sim.rl_wrapper import ActionMaskCoCEnv

DEFAULT_BASES = ["base07.json", "base08.json", "base09.json", "base10.json"]
DEFAULT_ARMIES = ["giant_barch", "mixed_wb", "hog_rush", "gowiva"]
DEFAULT_MODEL = "models/ppo_m7b_seed42.zip"

DOCS_DIR = ROOT / "docs"
GALLERY_DIR = DOCS_DIR / "gallery"
SHOWCASE_DIR = DOCS_DIR / "showcase"
LOGS_DIR = GALLERY_DIR / "logs"


def _clean_troop_name(troop_key: str) -> str:
    """Format raw troop key like 'hog_rider_l4' -> 'Hog Rider'."""
    clean = troop_key.split("_l")[0].replace("_", " ").title()
    return clean


def _get_fonts():
    """Load system truetype fonts or fallback to default."""
    try:
        font_bold = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 14)
        font_reg = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
        font_sm = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 11)
    except Exception:
        try:
            font_bold = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
            font_reg = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 12)
            font_sm = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 11)
        except Exception:
            font_bold = ImageFont.load_default()
            font_reg = ImageFont.load_default()
            font_sm = ImageFont.load_default()
    return font_bold, font_reg, font_sm


def record_side_by_side(
    base_file: str,
    army: str,
    model,
    out_path: Path,
    seed: int = 0,
    duration: int = 250,
    sample_every: int = 2,
    hold_frames: int = 6,
) -> dict:
    """Simulate left_wave and PPO, compositing frames into a side-by-side GIF."""
    font_bold, font_reg, font_sm = _get_fonts()

    # 1. Simulate left_wave
    env_lw = CoCEnv(base_file=base_file, army=army, render_mode="rgb_array")
    env_lw.reset(seed=seed)
    frames_lw = []
    actions_lw = []
    counts_lw = []
    deploy_events_lw = []
    done_lw = False
    step_lw = 0
    last_deploy_lw = "None"
    info_lw = {}

    while not done_lw:
        frame = env_lw.render()
        act = rule_based_action(env_lw, step_lw)
        if act[0] > 0:
            tr = _clean_troop_name(env_lw.troop_keys[act[0] - 1])
            ang = math.atan2(act[2] - 22, act[1] - 22)
            sec = int(((ang + math.pi) / (2 * math.pi)) * 16) % 16
            last_deploy_lw = f"{tr} @ s{sec}"
            deploy_events_lw.append((round(step_lw * 1.0, 1), tr, sec, 1))

        alive_lw = sum(1 for tr in env_lw.troops if tr.alive)
        dep_lw = sum(env_lw.army_template.values()) - sum(env_lw.army_left.values())

        if step_lw % sample_every == 0:
            frames_lw.append(Image.fromarray(frame))
            actions_lw.append(last_deploy_lw)
            counts_lw.append((alive_lw, dep_lw))

        _, _, term, trunc, info_lw = env_lw.step(act)
        done_lw = term or trunc
        step_lw += 1

    final_lw = Image.fromarray(env_lw.render())
    frames_lw.append(final_lw)
    actions_lw.append(last_deploy_lw)
    alive_lw = sum(1 for tr in env_lw.troops if tr.alive)
    dep_lw = sum(env_lw.army_template.values()) - sum(env_lw.army_left.values())
    counts_lw.append((alive_lw, dep_lw))
    th_lw = bool(env_lw.th_destroyed)
    env_lw.close()

    # 2. Simulate PPO
    env_ppo = ActionMaskCoCEnv(bases=[base_file], armies=[army], render_mode="rgb_array")
    obs, _ = env_ppo.reset(seed=seed)
    frames_ppo = []
    actions_ppo = []
    counts_ppo = []
    deploy_events_ppo = []
    done_ppo = False
    step_ppo = 0
    last_deploy_ppo = "None"
    info_ppo = {}

    while not done_ppo:
        frame = env_ppo.render()
        mask = env_ppo.action_masks()
        act, _ = model.predict(obs, deterministic=True, action_masks=mask)
        act = int(act)
        if act > 0:
            k = (act - 1) // 16
            sec = (act - 1) % 16
            tr = _clean_troop_name(env_ppo.troop_keys[k])
            last_deploy_ppo = f"{tr} @ s{sec}"
            deploy_events_ppo.append((round(step_ppo * 1.0, 1), tr, sec, 1))

        alive_ppo = sum(1 for tr in env_ppo.env.troops if tr.alive)
        dep_ppo = sum(env_ppo.env.army_template.values()) - sum(env_ppo.env.army_left.values())

        if step_ppo % sample_every == 0:
            frames_ppo.append(Image.fromarray(frame))
            actions_ppo.append(last_deploy_ppo)
            counts_ppo.append((alive_ppo, dep_ppo))

        obs, _, term, trunc, info_ppo = env_ppo.step(act)
        done_ppo = term or trunc
        step_ppo += 1

    final_ppo = Image.fromarray(env_ppo.render())
    frames_ppo.append(final_ppo)
    actions_ppo.append(last_deploy_ppo)
    alive_ppo = sum(1 for tr in env_ppo.env.troops if tr.alive)
    dep_ppo = sum(env_ppo.env.army_template.values()) - sum(env_ppo.env.army_left.values())
    counts_ppo.append((alive_ppo, dep_ppo))
    th_ppo = bool(env_ppo.env.th_destroyed)
    env_ppo.close()

    # 3. Write deployment logs to docs/gallery/logs/
    stem = f"{Path(base_file).stem}_{army}"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    lw_log_path = LOGS_DIR / f"{stem}_left_wave.csv"
    with open(lw_log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["second", "troop_type", "sector", "count"])
        for ev in deploy_events_lw:
            writer.writerow(ev)

    ppo_log_path = LOGS_DIR / f"{stem}_ppo.csv"
    with open(ppo_log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["second", "troop_type", "sector", "count"])
        for ev in deploy_events_ppo:
            writer.writerow(ev)

    comb_log_path = LOGS_DIR / f"{stem}.csv"
    with open(comb_log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["agent", "second", "troop_type", "sector", "count"])
        for ev in deploy_events_lw:
            writer.writerow(["left_wave", *ev])
        for ev in deploy_events_ppo:
            writer.writerow(["ppo", *ev])

    # 4. Composite frames
    w_panel, h_panel = 616, 616
    h_top = 52
    h_bot = 46
    sep = 4
    w_total = w_panel * 2 + sep
    h_total = h_top + h_panel + h_bot

    n_frames = max(len(frames_lw), len(frames_ppo))
    comp_frames = []

    dest_lw = info_lw.get("destruction", 0.0) * 100.0
    stars_lw = int(info_lw.get("stars", 0))
    dest_ppo = info_ppo.get("destruction", 0.0) * 100.0
    stars_ppo = int(info_ppo.get("stars", 0))

    th_lw_str = "Destroyed" if th_lw else "Alive"
    th_ppo_str = "Destroyed" if th_ppo else "Alive"

    if stars_ppo > stars_lw or (stars_ppo == stars_lw and dest_ppo > dest_lw):
        outcome_tag = "PPO WIN"
        ppo_color = (100, 255, 100)
        lw_color = (220, 220, 220)
    elif stars_lw > stars_ppo or (stars_lw == stars_ppo and dest_lw > dest_ppo):
        outcome_tag = "LW WIN"
        ppo_color = (220, 220, 220)
        lw_color = (255, 215, 0)
    else:
        outcome_tag = "TIE"
        ppo_color = (220, 220, 220)
        lw_color = (220, 220, 220)

    for i in range(n_frames):
        f_lw = frames_lw[min(i, len(frames_lw) - 1)]
        f_ppo = frames_ppo[min(i, len(frames_ppo) - 1)]
        a_lw = actions_lw[min(i, len(actions_lw) - 1)]
        a_ppo = actions_ppo[min(i, len(actions_ppo) - 1)]
        cnt_lw = counts_lw[min(i, len(counts_lw) - 1)]
        cnt_ppo = counts_ppo[min(i, len(counts_ppo) - 1)]

        comp = Image.new("RGB", (w_total, h_total), (20, 24, 20))
        comp.paste(f_lw, (0, h_top))
        comp.paste(f_ppo, (w_panel + sep, h_top))

        draw = ImageDraw.Draw(comp)

        # Top HUD bar (h_top = 52)
        draw.rectangle([0, 0, w_total, h_top], fill=(24, 30, 24))

        # Row 1: Centered Title
        title_txt = f"{base_file}  \u2014  {army} (seed {seed})"
        t_bbox = font_bold.getbbox(title_txt)
        t_w = t_bbox[2] - t_bbox[0]
        draw.text(((w_total - t_w) // 2, 6), title_txt, fill=(240, 240, 240), font=font_bold)

        # Row 2: Per-panel HUDs with troops alive / deployed counter
        hud_lw = f"LEFT_WAVE | Deploy: {a_lw} | Troops: {cnt_lw[0]}/{cnt_lw[1]}"
        hud_ppo = f"MASKABLE PPO | Deploy: {a_ppo} | Troops: {cnt_ppo[0]}/{cnt_ppo[1]}"
        draw.text((12, 28), hud_lw, fill=(255, 215, 0), font=font_bold)
        draw.text((w_panel + sep + 12, 28), hud_ppo, fill=(0, 220, 255), font=font_bold)

        # Vertical Separator
        draw.rectangle([w_panel, 0, w_panel + sep, h_total], fill=(10, 10, 10))

        # Bottom Caption bar
        draw.rectangle([0, h_top + h_panel, w_total, h_total], fill=(22, 26, 22))
        cap_lw = f"Final: {dest_lw:.1f}% dest | {stars_lw}* | Town Hall: {th_lw_str}"
        cap_ppo = f"Final: {dest_ppo:.1f}% dest | {stars_ppo}* | Town Hall: {th_ppo_str}"

        if outcome_tag == "LW WIN":
            cap_lw += " [WIN]"
        elif outcome_tag == "PPO WIN":
            cap_ppo += " [WIN]"

        draw.text((12, h_top + h_panel + 13), cap_lw, fill=lw_color, font=font_bold if outcome_tag == "LW WIN" else font_reg)
        draw.text((w_panel + sep + 12, h_top + h_panel + 13), cap_ppo, fill=ppo_color, font=font_bold if outcome_tag == "PPO WIN" else font_reg)

        comp_frames.append(comp.quantize(colors=256, method=Image.Quantize.MEDIANCUT))

    # Hold final frame
    for _ in range(hold_frames):
        comp_frames.append(comp_frames[-1])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    comp_frames[0].save(
        out_path,
        save_all=True,
        append_images=comp_frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
    )

    size_bytes = out_path.stat().st_size
    return {
        "base": base_file,
        "army": army,
        "lw_dest": round(dest_lw, 1),
        "lw_stars": stars_lw,
        "lw_th": th_lw,
        "ppo_dest": round(dest_ppo, 1),
        "ppo_stars": stars_ppo,
        "ppo_th": th_ppo,
        "outcome": outcome_tag,
        "frames": len(comp_frames),
        "size_kb": round(size_bytes / 1024, 1),
        "gif_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
    }


def generate_index_markdown(records: list[dict], out_path: Path) -> None:
    """Generate docs/gallery/index.md summarizing all recorded GIFs."""
    lines = [
        "# CoC-RL Battle Gallery: Side-by-Side Strategy Visualizations",
        "",
        "Animated side-by-side battle recordings comparing the baseline **`left_wave`** (left panel) against trained **`MaskablePPO`** (right panel, `seed42`, deterministic actions) on held-out bases (`base07.json` to `base10.json`) across key TH8 army compositions (`giant_barch`, `mixed_wb`, `hog_rush`, `gowiva`) at **seed 0** (250 ms / frame).",
        "",
        "---",
        "",
        "## Featured Showcase Battles",
        "",
        "The 4 most instructive animations are preserved in [`docs/showcase/`](../showcase/):",
        "",
        "1. **PPO Victory ([`docs/showcase/ppo_win_base09_hog_rush.gif`](../showcase/ppo_win_base09_hog_rush.gif) - 444.2 KB):**",
        "   - **Base:** `base09.json` | **Army:** `hog_rush`",
        "   - **Left Wave:** 59.3% dest, 1★, Town Hall Alive",
        "   - **MaskablePPO:** 100.0% dest, 3★, Town Hall Destroyed (**+40.7% dest, +2★**)",
        "   - *Tactical Analysis:* PPO distributes Hog Riders across multiple sectors, allowing them to jump walls, clear defense towers independently without grouping into Mortar splash, and easily wipe the Town Hall.",
        "",
        "2. **PPO Defeat ([`docs/showcase/ppo_loss_base08_gowiva.gif`](../showcase/ppo_loss_base08_gowiva.gif) - 610.6 KB):**",
        "   - **Base:** `base08.json` | **Army:** `gowiva`",
        "   - **Left Wave:** 100.0% dest, 3★, Town Hall Destroyed",
        "   - **MaskablePPO:** 40.7% dest, 0★, Town Hall Alive (**-59.3% dest, -3★**)",
        "   - *Tactical Analysis:* Demonstrates why PPO trails on stars with heavy ground armies. `left_wave` masses all Valkyries and Golems on a single flank, cutting directly through the core walls to the Town Hall for a complete 3-star wipe. PPO spreads its Golems and Valkyries around the perimeter, splitting its damage and stalling outside the walls with 0 stars.",
        "",
        "3. **3-Star Wipe ([`docs/showcase/three_star_base10_giant_barch.gif`](../showcase/three_star_base10_giant_barch.gif) - 653.4 KB):**",
        "   - **Base:** `base10.json` | **Army:** `giant_barch`",
        "   - **Left Wave:** 100.0% dest, 3★, Town Hall Destroyed",
        "   - **MaskablePPO:** 100.0% dest, 3★, Town Hall Destroyed (**Tie**)",
        "   - *Tactical Analysis:* An open layout with few interior wall barriers allows both massed single-flank rushes and multi-sector perimeter deployments to overwhelm point defenses and wipe 100% of the base.",
        "",
        "4. **Compartment Stalemate ([`docs/showcase/failure_base07_giant_barch.gif`](../showcase/failure_base07_giant_barch.gif) - 576.5 KB):**",
        "   - **Base:** `base07.json` | **Army:** `giant_barch`",
        "   - **Left Wave:** 11.1% dest, 0★, Town Hall Alive",
        "   - **MaskablePPO:** 25.9% dest, 0★, Town Hall Alive (**0★ for both**)",
        "   - *Tactical Analysis:* Heavily walled concentric compartments neutralize standard ground armies without jump or mass wall breakers. Both agents stall against the outer perimeter defenses and fail to breach the core.",
        "",
        "---",
        "",
        "## Summary of All 16 Battles",
        "",
        "| Base | Army | Left Wave (Dest / Stars / TH) | PPO (Dest / Stars / TH) | Delta Dest | Delta Stars | Outcome | Animation |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for r in records:
        b = r["base"]
        a = r["army"]
        lw_str = f"{r['lw_dest']:.1f}% / {r['lw_stars']}★ / {'TH' if r['lw_th'] else 'no-TH'}"
        ppo_str = f"{r['ppo_dest']:.1f}% / {r['ppo_stars']}★ / {'TH' if r['ppo_th'] else 'no-TH'}"
        d_dest = r["ppo_dest"] - r["lw_dest"]
        d_stars = r["ppo_stars"] - r["lw_stars"]
        d_dest_str = f"{d_dest:+.1f}%"
        d_stars_str = f"{d_stars:+d}"
        gif_file = Path(r["gif_path"]).name
        lines.append(
            f"| `{b}` | `{a}` | {lw_str} | {ppo_str} | {d_dest_str} | {d_stars_str} | **{r['outcome']}** | [{gif_file}]({gif_file}) |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Key Tactical Insights from the Gallery",
        "",
        "1. **Core Penetration vs Perimeter Dispersion:** On layouts where `left_wave` breaks through outer walls (`base08` `gowiva`), massing all units along a single flank enables high-dps Valkyries to cut through to the Town Hall for a 3-star clear. In contrast, PPO's multi-sector deployments diffuse attack power across multiple compartments, stalling outside the core.",
        "2. **Hog Rider Wall Bypass:** On `base09` `hog_rush`, PPO's distributed deployment around multiple defensive sectors enables Hog Riders to path cleanly between outer defenses and clear defensive towers without bunching into Mortar splash, achieving an uncontested 100% 3-star wipe (+40.7% over `left_wave`).",
        "3. **Open Base Bulldozing:** On `base10` `giant_barch`, the wide open courtyard layout allows both strategies to overwhelm point defenses and achieve complete 100% 3-star wipes.",
        "4. **Compartmentalized Stalemates:** On `base07`, heavy interior wall rings stop both `left_wave` and `PPO` `giant_barch` outside the core (0 stars for both), highlighting the difficulty of compartmented layouts for basic ground armies.",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Record side-by-side CoC-RL battle GIFs.")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Path to PPO model zip.")
    parser.add_argument("--bases", nargs="+", default=DEFAULT_BASES, help="Bases to evaluate.")
    parser.add_argument("--armies", nargs="+", default=DEFAULT_ARMIES, help="Armies to evaluate.")
    parser.add_argument("--seed", type=int, default=0, help="Simulation seed.")
    parser.add_argument("--duration", type=int, default=250, help="Frame duration in ms.")
    parser.add_argument("--time-limit", type=int, default=600, help="Maximum execution time in seconds.")
    parser.add_argument("--showcase-only", action="store_true", help="Only record the 4 showcase battles.")
    args = parser.parse_args()

    t_start = time.perf_counter()
    print("=" * 80)
    print("RECORD GALLERY: Side-by-Side Battles (left_wave vs MaskablePPO)")
    print(f"Showcase Only: {args.showcase_only}")
    print(f"Bases: {args.bases}")
    print(f"Armies: {args.armies}")
    print(f"Model: {args.model} | Seed: {args.seed} | Duration: {args.duration}ms")
    print(f"Output Gallery: {GALLERY_DIR}")
    print(f"Output Showcase: {SHOWCASE_DIR}")
    print(f"Output Logs: {LOGS_DIR}")
    print("=" * 80, flush=True)

    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    SHOWCASE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    from sb3_contrib import MaskablePPO
    model = MaskablePPO.load(args.model, device="cpu")

    showcase_combos = [
        ("base09.json", "hog_rush", "ppo_win_base09_hog_rush.gif"),
        ("base08.json", "gowiva", "ppo_loss_base08_gowiva.gif"),
        ("base10.json", "giant_barch", "three_star_base10_giant_barch.gif"),
        ("base07.json", "giant_barch", "failure_base07_giant_barch.gif"),
    ]

    if args.showcase_only:
        targets_to_run = [(b, a) for b, a, _ in showcase_combos]
    else:
        targets_to_run = [(b, a) for b in args.bases for a in args.armies]

    records = []
    total_combos = len(targets_to_run)
    idx = 0

    for b, a in targets_to_run:
        idx += 1
        if time.perf_counter() - t_start > args.time_limit:
            print(f"Time limit reached ({args.time_limit}s), stopping.", flush=True)
            break

        stem = f"{Path(b).stem}_{a}"
        gif_path = GALLERY_DIR / f"{stem}.gif"
        t0 = time.perf_counter()
        print(f"[{idx}/{total_combos}] Recording {stem} ...", end="", flush=True)

        res = record_side_by_side(
            base_file=b,
            army=a,
            model=model,
            out_path=gif_path,
            seed=args.seed,
            duration=args.duration,
        )
        records.append(res)
        dt = time.perf_counter() - t0
        print(f" Done ({dt:.1f}s, {res['frames']} frames, {res['size_kb']} KB) | Outcome: {res['outcome']}", flush=True)

    # Write gallery index.md if full run
    if not args.showcase_only:
        index_path = GALLERY_DIR / "index.md"
        generate_index_markdown(records, index_path)
        print(f"\nWrote gallery index to {index_path}", flush=True)

    # Copy showcase targets to docs/showcase/
    print("\n--- Updating Showcase GIFs & Logs ---", flush=True)
    showcase_lines = [
        "# Showcase Battles: Left Wave vs MaskablePPO",
        "",
        "Selected representative side-by-side battle animations comparing `left_wave` (left) against `MaskablePPO` (right, seed 42) at 250 ms / frame (all files under 2 MB).",
        "",
    ]

    for b, a, showcase_name in showcase_combos:
        stem = f"{Path(b).stem}_{a}"
        src = GALLERY_DIR / f"{stem}.gif"
        dst = SHOWCASE_DIR / showcase_name
        if src.exists():
            shutil.copy2(src, dst)
            size_kb = dst.stat().st_size / 1024
            size_mb = size_kb / 1024
            print(f"Copied {src.name} -> {dst} ({size_kb:.1f} KB, {size_mb:.2f} MB)", flush=True)
            assert size_mb < 2.0, f"Showcase GIF {dst.name} exceeds 2 MB ({size_mb:.2f} MB)"
            showcase_lines.append(f"### `{showcase_name}` ({size_kb:.1f} KB)\n![{showcase_name}]({showcase_name})\n")
        else:
            print(f"Warning: source GIF {src} not found", flush=True)

        # Mirror logs to showcase-named CSVs for convenience
        sc_stem = Path(showcase_name).stem
        for suffix in ["_left_wave.csv", "_ppo.csv", ".csv"]:
            src_log = LOGS_DIR / f"{stem}{suffix}"
            if src_log.exists():
                dst_log = LOGS_DIR / f"{sc_stem}{suffix}"
                shutil.copy2(src_log, dst_log)

    (SHOWCASE_DIR / "README.md").write_text("\n".join(showcase_lines), encoding="utf-8")
    print(f"\nAll tasks finished in {time.perf_counter() - t_start:.1f}s.", flush=True)


if __name__ == "__main__":
    main()

