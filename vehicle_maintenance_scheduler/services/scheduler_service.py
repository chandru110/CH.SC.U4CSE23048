from __future__ import annotations

from typing import Any

from middleware.logger import Log
from models.schemas import Depot, VehicleTask


class SchedulerError(RuntimeError):
    pass


async def optimize_schedule(depot: Depot, vehicle_task_dicts: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    """
    0/1 Knapsack optimization (dynamic programming).

    - Each task has `duration` (weight) and `impact` (value)
    - Capacity is depot.mechanicHours
    - Goal: maximize total impact within mechanic hours
    """

    capacity = int(depot.mechanicHours)
    if capacity < 0:
        raise SchedulerError("Depot mechanicHours must be non-negative")

    tasks: list[VehicleTask] = []
    raw_by_index: list[dict[str, Any]] = []
    for obj in vehicle_task_dicts:
        try:
            task = VehicleTask.from_api(obj)
            if task.duration is None or task.impact is None:
                continue
            if task.duration <= 0 or task.impact < 0:
                continue
            tasks.append(task)
            raw_by_index.append(obj)
        except Exception:
            # Skip malformed tasks; keep the optimizer robust.
            continue

    n = len(tasks)
    await Log("backend", "info", "service", f"Optimizing schedule with {n} tasks and capacity {capacity}.")

    # dp[w] = best impact for capacity w using processed items
    dp = [0] * (capacity + 1)
    # keep[i][w] indicates taking item i at capacity w after processing i
    keep = [[False] * (capacity + 1) for _ in range(n)]

    for i, task in enumerate(tasks):
        w_i = int(task.duration)
        v_i = int(task.impact)
        # Traverse backwards to enforce 0/1 (each item used at most once).
        for w in range(capacity, w_i - 1, -1):
            candidate = dp[w - w_i] + v_i
            if candidate > dp[w]:
                dp[w] = candidate
                keep[i][w] = True

    max_impact = dp[capacity]

    # Reconstruct chosen items.
    selected: list[dict[str, Any]] = []
    w = capacity
    for i in range(n - 1, -1, -1):
        if keep[i][w]:
            selected.append(raw_by_index[i])
            w -= int(tasks[i].duration)

    selected.reverse()
    await Log("backend", "info", "service", f"Optimization complete. maxImpact={max_impact}, selectedTasks={len(selected)}.")
    return max_impact, selected
