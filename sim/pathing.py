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
    grid = wall_grid.tolist()
    if grid[sy][sx]:
        return None

    # Goal distance allows reaching adjacent tile centers for melee/1x1 walls.
    goal_reach = target_size / 2.0 + max(0.6, attack_range)
    goal_reach2 = goal_reach * goal_reach
    hypot = math.hypot
    heappop = heapq.heappop
    heappush = heapq.heappush

    dx0 = sx + 0.5 - target_cx
    dy0 = sy + 0.5 - target_cy
    if dx0 * dx0 + dy0 * dy0 <= goal_reach2:
        return []

    start_idx = sy * w + sx
    n = w * h
    closed = [False] * n
    g_score = [float("inf")] * n
    came_from = [-1] * n
    g_score[start_idx] = 0.0
    h0 = max(0.0, hypot(dx0, dy0) - goal_reach)
    open_heap: list[tuple[float, int, int, int]] = [(h0, start_idx, sx, sy)]

    while open_heap:
        _, ci, cx, cy = heappop(open_heap)
        if closed[ci]:
            continue
        gx = cx + 0.5 - target_cx
        gy = cy + 0.5 - target_cy
        if gx * gx + gy * gy <= goal_reach2:
            path: list[tuple[float, float]] = []
            cur = ci
            while cur != start_idx:
                path.append(((cur % w) + 0.5, (cur // w) + 0.5))
                cur = came_from[cur]
            path.reverse()
            return path
        closed[ci] = True
        base_g = g_score[ci]
        row_c = grid[cy]

        for dx, dy, step_cost in _DIRS:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            ni = ny * w + nx
            if closed[ni]:
                continue
            if grid[ny][nx]:
                continue
            if dx != 0 and dy != 0 and (row_c[nx] or grid[ny][cx]):
                continue
            ng = base_g + step_cost
            if ng < g_score[ni]:
                g_score[ni] = ng
                came_from[ni] = ci
                hd = hypot(nx + 0.5 - target_cx, ny + 0.5 - target_cy) - goal_reach
                heappush(open_heap, (ng + (hd if hd > 0.0 else 0.0), ni, nx, ny))

    return None
