"""Interactive human play script: select troop with keys 1-5 and left-click grid to deploy."""

import argparse
import pygame

from sim import CoCEnv


def run_human(base_file="base03.json", army="giant_barch", seed=0, max_frames=None):
    env = CoCEnv(base_file=base_file, army=army, render_mode="rgb_array")
    env.reset(seed=seed)
    pygame.init()

    cell = 14
    grid_px = env.grid * cell
    hud_h = 56
    screen = pygame.display.set_mode((grid_px, grid_px + hud_h))
    pygame.display.set_caption("coc-rl Human Play")
    font = pygame.font.SysFont("consolas", 13, bold=True)
    clock = pygame.time.Clock()

    selected_idx = 0
    running = True
    frames = 0
    tick_acc = 0
    pending_action = [0, 0, 0]

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    env.reset(seed=seed)
                    pending_action = [0, 0, 0]
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    if idx < len(env.troop_keys):
                        selected_idx = idx
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if my < grid_px:
                    gx, gy = mx // cell, my // cell
                    pending_action = [selected_idx + 1, gx, gy]

        tick_acc += 1
        if tick_acc >= 5:
            tick_acc = 0
            _, _, term, trunc, _ = env.step(pending_action)
            pending_action = [0, 0, 0]
            if term or trunc:
                pending_action = [0, 0, 0]

        frame = env.render()
        surf = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
        screen.blit(surf, (0, 0))
        pygame.draw.rect(screen, (28, 32, 36), (0, grid_px, grid_px, hud_h))

        labels = []
        for idx, k in enumerate(env.troop_keys):
            mark = ">" if idx == selected_idx else " "
            labels.append(f"{mark}[{idx+1}] {env.troop_defs[k]['name']}: {env.army_left[k]}")
        line1 = "  ".join(labels[:3])
        line2 = "  ".join(labels[3:]) + "   | Click grid to deploy | R=reset Esc=quit"
        screen.blit(font.render(line1, True, (235, 235, 235)), (8, grid_px + 6))
        screen.blit(font.render(line2, True, (185, 200, 210)), (8, grid_px + 30))

        pygame.display.flip()
        clock.tick(30)
        frames += 1
        if max_frames is not None and frames >= max_frames:
            running = False

    env.close()
    pygame.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="base03.json")
    parser.add_argument("--army", default="giant_barch")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--smoke-test", action="store_true", help="Run 3 frames and exit cleanly")
    args = parser.parse_args()
    run_human(base_file=args.base, army=args.army, seed=args.seed, max_frames=3 if args.smoke_test else None)


if __name__ == "__main__":
    main()

