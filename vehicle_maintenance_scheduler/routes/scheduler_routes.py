from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from middleware.logger import Log
from models.schemas import Depot, ScheduleResponse
from services.api_service import fetch_depots, fetch_vehicles
from services.scheduler_service import optimize_schedule


router = APIRouter(tags=["scheduler"])


@router.get("/schedule/{depot_id}", response_model=ScheduleResponse)
async def get_schedule(depot_id: int) -> ScheduleResponse:
    await Log("backend", "info", "route", f"GET /schedule/{depot_id} called.")

    try:
        depots_raw: list[dict[str, Any]] = await fetch_depots()
        vehicles_raw: list[dict[str, Any]] = await fetch_vehicles()
    except Exception as exc:  # noqa: BLE001
        await Log("backend", "error", "route", f"Failed to fetch inputs: {exc}")
        raise HTTPException(status_code=502, detail="Failed to fetch inputs from evaluation service") from exc

    depot_obj: Depot | None = None
    for d in depots_raw:
        try:
            depot = Depot.parse_obj(d)
            if depot.resolved_id() == depot_id:
                depot_obj = depot
                break
        except Exception:
            continue

    if depot_obj is None:
        await Log("backend", "warn", "route", f"Depot not found: depot_id={depot_id}")
        raise HTTPException(status_code=404, detail="Depot not found")

    try:
        max_impact, selected_tasks = await optimize_schedule(depot_obj, vehicles_raw)
    except Exception as exc:  # noqa: BLE001
        await Log("backend", "error", "route", f"Scheduling failed: {exc}")
        raise HTTPException(status_code=500, detail="Scheduling failed") from exc

    return ScheduleResponse(
        depot_id=depot_id,
        mechanic_hours=int(depot_obj.mechanicHours),
        maxImpact=int(max_impact),
        selectedTasks=selected_tasks,
    )
