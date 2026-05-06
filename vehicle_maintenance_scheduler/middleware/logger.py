from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx

from utils.constants import (
    ALLOWED_LEVEL_VALUES,
    ALLOWED_PACKAGE_VALUES,
    ALLOWED_STACK_VALUES,
    EVAL_PATHS,
    get_settings,
)


Stack = Literal["backend"]
Level = Literal["debug", "info", "warn", "error", "fatal"]
Package = Literal[
    "cache",
    "controller",
    "cron_job",
    "db",
    "domain",
    "handler",
    "repository",
    "route",
    "service",
    "auth",
    "middleware",
    "utils",
]


_local_logger = logging.getLogger("vehicle_maintenance_scheduler")


class ExternalLogger:
    """
    Sends logs to the evaluation service.

    This logger is intentionally tolerant:
    - If token is missing, it will only log locally.
    - If the external call fails, it will not crash the app.
    """

    def __init__(self) -> None:
        self._token_provider: callable[[], str | None] | None = None
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    def set_token_provider(self, provider: callable[[], str | None]) -> None:
        self._token_provider = provider

    async def _get_client(self) -> httpx.AsyncClient:
        async with self._lock:
            if self._client is None:
                settings = get_settings()
                self._client = httpx.AsyncClient(
                    base_url=settings.eval_base_url,
                    timeout=httpx.Timeout(20.0),
                    headers={"Content-Type": "application/json"},
                )
            return self._client

    async def aclose(self) -> None:
        async with self._lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def log(self, stack: Stack, level: Level, package: Package, message: str) -> None:
        # Always log locally (useful when the evaluation logger is unavailable).
        _local_logger.info("[%s/%s/%s] %s", stack, level, package, message)

        # Validate allowed values to avoid rejected payloads.
        if stack not in ALLOWED_STACK_VALUES or level not in ALLOWED_LEVEL_VALUES or package not in ALLOWED_PACKAGE_VALUES:
            _local_logger.warning("Skipped external log due to invalid fields: %s %s %s", stack, level, package)
            return

        token = self._token_provider() if self._token_provider else None
        if not token:
            return

        payload: dict[str, Any] = {"stack": stack, "level": level, "package": package, "message": message}
        try:
            client = await self._get_client()
            resp = await client.post(
                EVAL_PATHS.logs,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - we must never crash from logging
            _local_logger.warning("External log failed: %s", exc)


external_logger = ExternalLogger()


async def Log(stack: Stack, level: Level, package: Package, message: str) -> None:
    """
    Required API by the assessment: Log(stack, level, package, message).
    """

    await external_logger.log(stack=stack, level=level, package=package, message=message)
