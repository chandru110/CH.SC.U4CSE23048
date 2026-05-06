from __future__ import annotations

import asyncio
from typing import Any

import httpx

from middleware.logger import Log
from services.auth_service import authenticate, get_access_token
from utils.constants import EVAL_PATHS, get_settings


class ApiServiceError(RuntimeError):
    pass


_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_client() -> httpx.AsyncClient:
    async with _client_lock:
        global _client
        if _client is None:
            settings = get_settings()
            _client = httpx.AsyncClient(
                base_url=settings.eval_base_url,
                timeout=httpx.Timeout(20.0),
                verify=settings.eval_verify_ssl,
                headers={"Content-Type": "application/json"},
            )
        return _client


async def close_client() -> None:
    async with _client_lock:
        global _client
        if _client is not None:
            await _client.aclose()
            _client = None


async def _auth_header() -> dict[str, str]:
    token = get_access_token()
    if not token:
        token = await authenticate()
    return {"Authorization": f"Bearer {token}"}


async def fetch_depots() -> list[dict[str, Any]]:
    await Log("backend", "debug", "service", "Fetching depots from evaluation service.")
    try:
        client = await get_client()
        resp = await client.get(EVAL_PATHS.depots, headers=await _auth_header())
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        await Log("backend", "error", "service", f"fetch_depots failed: {exc}")
        raise ApiServiceError(f"fetch_depots failed: {exc}") from exc

    # Some APIs wrap payloads (e.g., {"data": [...]}); support both.
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"]
    if isinstance(data, list):
        return data
    raise ApiServiceError("Unexpected depots response format")


async def fetch_vehicles() -> list[dict[str, Any]]:
    await Log("backend", "debug", "service", "Fetching vehicles from evaluation service.")
    try:
        client = await get_client()
        resp = await client.get(EVAL_PATHS.vehicles, headers=await _auth_header())
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        await Log("backend", "error", "service", f"fetch_vehicles failed: {exc}")
        raise ApiServiceError(f"fetch_vehicles failed: {exc}") from exc

    if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
        return data["data"]
    if isinstance(data, list):
        return data
    raise ApiServiceError("Unexpected vehicles response format")
