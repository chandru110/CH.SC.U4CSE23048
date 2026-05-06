from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from middleware.logger import Log, external_logger
from routes.scheduler_routes import router as scheduler_router
from services.api_service import close_client
from services.auth_service import _state as auth_state, authenticate, register_if_needed
from utils.constants import load_environment


def _configure_local_logging() -> None:
    """
    Local logging is useful for development + as a fallback when external logging fails.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_environment()
    _configure_local_logging()

    await Log("backend", "info", "middleware", "Application starting up.")

    # Startup steps required by the assessment:
    # - register user (obtain client credentials)
    # - generate auth token
    # - log startup success
    try:
        await register_if_needed()
        if auth_state.client_id and auth_state.client_secret:
            await authenticate()
            await Log("backend", "info", "middleware", "Startup success: registered + authenticated.")
        else:
            await Log(
                "backend", "warn", "middleware",
                "No client credentials available. Set EVAL_CLIENT_ID and EVAL_CLIENT_SECRET in .env and restart.",
            )
    except Exception as exc:  # noqa: BLE001
        # We still let the app start so routes can show the error clearly.
        await Log("backend", "fatal", "middleware", f"Startup initialization failed: {exc}")

    yield

    await Log("backend", "info", "middleware", "Application shutting down.")
    await close_client()
    await external_logger.aclose()


app = FastAPI(title="vehicle_maintenance_scheduler", version="1.0.0", lifespan=lifespan)
app.include_router(scheduler_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        await Log(
            "backend",
            "info",
            "middleware",
            f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.1f}ms)",
        )
        return response
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        await Log(
            "backend",
            "error",
            "middleware",
            f"{request.method} {request.url.path} -> 500 ({elapsed_ms:.1f}ms) error={exc}",
        )
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    await Log("backend", "error", "handler", f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
