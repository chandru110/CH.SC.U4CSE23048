from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    email: str
    name: str
    mobileNo: str
    githubUsername: str
    rollNo: str
    accessCode: str = Field(default="PTBMmQ")


class RegisterResponse(BaseModel):
    clientID: str = Field(alias="clientID")
    clientSecret: str = Field(alias="clientSecret")


class AuthRequest(BaseModel):
    email: str
    name: str
    rollNo: str
    accessCode: str
    clientID: str
    clientSecret: str


class AuthResponse(BaseModel):
    access_token: str


class Depot(BaseModel):
    """
    The evaluation service contract may evolve; we keep a strict model for the
    scheduling fields while allowing extra keys.
    """

    id: int | None = None
    depot_id: int | None = None
    mechanicHours: int = Field(alias="mechanicHours")

    class Config:
        extra = "allow"
        allow_population_by_field_name = True

    def resolved_id(self) -> int:
        if self.id is not None:
            return int(self.id)
        if self.depot_id is not None:
            return int(self.depot_id)
        raise ValueError("Depot has no id field")


class VehicleTask(BaseModel):
    """
    Represents a single vehicle maintenance task for knapsack optimization.
    We accept multiple possible key names to be resilient to contract variations.
    """

    id: int | str | None = None
    duration: int | None = None
    impact: int | None = None

    class Config:
        extra = "allow"

    @staticmethod
    def from_api(obj: dict[str, Any]) -> "VehicleTask":
        duration = (
            obj.get("duration")
            or obj.get("Duration")
            or obj.get("time")
            or obj.get("maintenanceDuration")
            or obj.get("hours")
        )
        impact = obj.get("impact") or obj.get("Impact") or obj.get("priority") or obj.get("score")
        task_id = obj.get("id") or obj.get("taskId") or obj.get("vehicleId") or obj.get("vehicle_id")

        return VehicleTask(id=task_id, duration=int(duration), impact=int(impact), **obj)


class ScheduleResponse(BaseModel):
    depot_id: int
    mechanic_hours: int
    maxImpact: int
    selectedTasks: list[dict[str, Any]]
