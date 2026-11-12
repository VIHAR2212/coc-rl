"""Grid A* pathfinding around 1x1 walls on the CoC 44x44 map."""

import heapq
import math
import numpy as np

_SQRT2 = math.sqrt(2)
_DIRS = (
    (1, 0, 1.0),
    (-1, 0, 1.0),
    (0, 1, 1.0),
    (0, -1, 1.0),
    (1, 1, _SQRT2),
    (1, -1, _SQRT2),
    (-1, 1, _SQRT2),
    (-1, -1, _SQRT2),
)


def astar_path(
    wall_grid: np.ndarray,
    start: tuple[int, int],
    target_cx: float,
    target_cy: float,
    target_size: int,
    attack_range: float,
) -> list[tuple[float, float]] | None:
    """Find a path from start tile to any passable tile within attack range of target.

    Returns a list of (x, y) tile-center waypoints (excluding start), or None if blocked.
    """
    h, w = wall_grid.shape
    sx, sy = start
    sx = max(0, min(w - 1, sx))
    sy = max(0, min(h - 1, sy))
    if wall_grid[sy, sx]:
        return None

    # Goal distance allows reaching adjacent tile centers for melee/1x1 walls.
    goal_reach = target_size / 2.0 + max(0.6, attack_range)

    def is_goal(x: int, y: int) -> bool:
        return math.hypot(x + 0.5 - target_cx, y + 0.5 - target_cy) <= goal_reach

    if is_goal(sx, sy):
        return []

    def heuristic(x: int, y: int) -> float:
        return max(0.0, math.hypot(x + 0.5 - target_cx, y + 0.5 - target_cy) - goal_reach)

    open_heap: list[tuple[float, int, int]] = [(heuristic(sx, sy), sx, sy)]
    g_score: dict[tuple[int, int], float] = {(sx, sy): 0.0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    closed: set[tuple[int, int]] = set()

    while open_heap:
        _, cx, cy = heapq.heappop(open_heap)
        if (cx, cy) in closed:
            continue
        if is_goal(cx, cy):
            path: list[tuple[float, float]] = []
            cur = (cx, cy)
            while cur != (sx, sy):
                path.append((cur[0] + 0.5, cur[1] + 0.5))
                cur = came_from[cur]
            path.reverse()
            return path
        closed.add((cx, cy))
        base_g = g_score[(cx, cy)]

        for dx, dy, step_cost in _DIRS:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in closed:
                continue
            if wall_grid[ny, nx]:
                continue
            if dx != 0 and dy != 0 and (wall_grid[cy, nx] or wall_grid[ny, cx]):
                continue
            ng = base_g + step_cost
            if ng < g_score.get((nx, ny), float("inf")):
                g_score[(nx, ny)] = ng
                came_from[(nx, ny)] = (cx, cy)
                heapq.heappush(open_heap, (ng + heuristic(nx, ny), nx, ny))

    return None
