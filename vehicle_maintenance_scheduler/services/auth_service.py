from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import httpx

from middleware.logger import Log, external_logger
from models.schemas import AuthRequest, AuthResponse, RegisterRequest, RegisterResponse
from utils.constants import EVAL_PATHS, get_settings


class AuthServiceError(RuntimeError):
    pass


@dataclass
class AuthState:
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None


_state = AuthState()
_lock = asyncio.Lock()


def get_access_token() -> str | None:
    return _state.access_token


def _upsert_env_file_kv(env_path: str, key: str, value: str) -> None:
    """
    Persist client credentials into `.env` so restarts can skip register.

    This is intentionally tiny and dependency-free.
    """

    lines: list[str] = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    found = False
    out: list[str] = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")

    with open(env_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")


def _persist_client_credentials(client_id: str, client_secret: str) -> None:
    # `.env` is expected to live in the project root (cwd when running uvicorn).
    env_path = os.path.join(os.getcwd(), ".env")
    _upsert_env_file_kv(env_path, "EVAL_CLIENT_ID", client_id)
    _upsert_env_file_kv(env_path, "EVAL_CLIENT_SECRET", client_secret)


async def register_if_needed() -> None:
    """
    Calls the evaluation registration endpoint to obtain client credentials.
    If env provides `EVAL_CLIENT_ID`/`EVAL_CLIENT_SECRET`, registration is skipped.
    """

    settings = get_settings()
    async with _lock:
        if _state.client_id and _state.client_secret:
            return

        if settings.eval_client_id and settings.eval_client_secret:
            _state.client_id = settings.eval_client_id
            _state.client_secret = settings.eval_client_secret
            await Log(
                "backend", "info", "auth", "Loaded client credentials from environment."
            )
            return

        payload = RegisterRequest(
            email=settings.affordmed_email,
            name=settings.affordmed_name,
            mobileNo=settings.affordmed_mobile_no,
            githubUsername=settings.affordmed_github_username,
            rollNo=settings.affordmed_roll_no,
            accessCode=settings.affordmed_access_code,
        ).dict(by_alias=True)

        await Log(
            "backend", "info", "auth", "Registering client with evaluation service."
        )

        try:
            async with httpx.AsyncClient(
                base_url=settings.eval_base_url,
                timeout=httpx.Timeout(20.0),
                headers={"Accept": "application/json"},
                follow_redirects=True,
            ) as client:
                resp = await client.post(EVAL_PATHS.register, json=payload)
                if resp.status_code == 409:
                    # Already registered: try to extract credentials from the 409 body.
                    body_preview = (resp.text or "").strip()
                    if len(body_preview) > 500:
                        body_preview = body_preview[:500] + "..."
                    await Log(
                        "backend",
                        "warn",
                        "auth",
                        f"Registration conflict (409). body={body_preview!r}",
                    )
                    # Try to parse credentials from the 409 response body.
                    try:
                        conflict_data = resp.json()
                        if (
                            "clientID" in conflict_data
                            and "clientSecret" in conflict_data
                        ):
                            data = conflict_data
                            await Log(
                                "backend",
                                "info",
                                "auth",
                                "Extracted credentials from 409 response.",
                            )
                        else:
                            data = None
                    except Exception:
                        data = None
                else:
                    if resp.status_code >= 400:
                        body_preview = (resp.text or "").strip()
                        if len(body_preview) > 500:
                            body_preview = body_preview[:500] + "..."
                        await Log(
                            "backend",
                            "error",
                            "auth",
                            f"Registration failed: {resp.status_code} body={body_preview!r}",
                        )
                        resp.raise_for_status()
                    data = resp.json()
        except Exception as exc:  # noqa: BLE001
            await Log("backend", "error", "auth", f"Registration failed: {exc}")
            raise AuthServiceError(f"Registration failed: {exc}") from exc

        # If 409 didn't include parsable credentials, log warning but don't crash.
        if data is None:
            await Log(
                "backend",
                "warn",
                "auth",
                "Already registered (409) but no credentials returned. "
                "Set EVAL_CLIENT_ID and EVAL_CLIENT_SECRET in .env from your first registration.",
            )
            return

        try:
            parsed = RegisterResponse.parse_obj(data)
        except Exception as exc:  # noqa: BLE001
            await Log(
                "backend", "error", "auth", f"Registration response parse failed: {exc}"
            )
            raise AuthServiceError(
                f"Registration response parse failed: {exc}"
            ) from exc

        _state.client_id = parsed.clientID
        _state.client_secret = parsed.clientSecret
        try:
            _persist_client_credentials(_state.client_id, _state.client_secret)
            await Log(
                "backend", "info", "auth", "Persisted client credentials into .env."
            )
        except Exception as exc:  # noqa: BLE001
            await Log(
                "backend",
                "warn",
                "auth",
                f"Failed to persist credentials into .env: {exc}",
            )

        await Log(
            "backend",
            "info",
            "auth",
            "Registration successful; client credentials stored in-memory.",
        )


async def authenticate() -> str:
    """
    Exchanges client credentials for a bearer token and stores it in-memory.
    """

    settings = get_settings()
    async with _lock:
        if _state.access_token:
            return _state.access_token

        if not _state.client_id or not _state.client_secret:
            raise AuthServiceError(
                "Missing client credentials; call register_if_needed() first."
            )

        client_id = _state.client_id
        client_secret = _state.client_secret
        await Log(
            "backend",
            "info",
            "auth",
            f"Requesting access token (clientID=***{client_id[-4:] if client_id else 'none'}).",
        )

        # Some evaluation-service deployments expect `clientID` while others expect `clientId`.
        # We attempt both to be resilient.
        payload_variants = [
            AuthRequest(clientID=client_id, clientSecret=client_secret).dict(
                by_alias=True
            ),
            {"clientId": client_id, "clientSecret": client_secret},
        ]

        last_error: Exception | None = None
        data = None
        for attempt, payload in enumerate(payload_variants, start=1):
            try:
                async with httpx.AsyncClient(
                    base_url=settings.eval_base_url,
                    timeout=httpx.Timeout(20.0),
                    headers={"Accept": "application/json"},
                    follow_redirects=True,
                ) as client:
                    resp = await client.post(EVAL_PATHS.auth, json=payload)
                    if resp.status_code >= 400:
                        # Log server-provided details to help debug 403/401.
                        body_preview = (resp.text or "").strip()
                        if len(body_preview) > 500:
                            body_preview = body_preview[:500] + "..."
                        await Log(
                            "backend",
                            "error",
                            "auth",
                            f"Auth attempt {attempt} failed: {resp.status_code} body={body_preview!r}",
                        )
                        resp.raise_for_status()
                    data = resp.json()
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        if data is None:
            await Log(
                "backend", "error", "auth", f"Auth failed after retries: {last_error}"
            )
            raise AuthServiceError(
                f"Auth failed after retries: {last_error}"
            ) from last_error

        try:
            parsed = AuthResponse.parse_obj(data)
        except Exception as exc:  # noqa: BLE001
            await Log("backend", "error", "auth", f"Auth response parse failed: {exc}")
            raise AuthServiceError(f"Auth response parse failed: {exc}") from exc

        _state.access_token = parsed.access_token

        # Let the logging middleware attach the token automatically.
        external_logger.set_token_provider(get_access_token)
        await Log(
            "backend",
            "info",
            "auth",
            "Authentication successful; bearer token stored in-memory.",
        )

        return _state.access_token
