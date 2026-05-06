from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from pydantic import BaseSettings, Field


def load_environment() -> None:
    """
    Load environment variables from `.env` at process start.

    We keep this as a small, explicit function (instead of auto-import side effects)
    so `main.py` can control when env is loaded.
    """

    load_dotenv(override=False)


@dataclass(frozen=True)
class EvalServicePaths:
    register: str = "/evaluation-service/register"
    auth: str = "/evaluation-service/auth"
    logs: str = "/evaluation-service/logs"
    depots: str = "/evaluation-service/depots"
    vehicles: str = "/evaluation-service/vehicles"


EVAL_PATHS = EvalServicePaths()


ALLOWED_STACK_VALUES = {"backend"}
ALLOWED_LEVEL_VALUES = {"debug", "info", "warn", "error", "fatal"}
ALLOWED_PACKAGE_VALUES = {
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
}


class Settings(BaseSettings):
    """
    Central settings model (Pydantic) with values sourced from environment variables.
    `.env` is loaded via `load_environment()` before Settings() is instantiated.
    """

    eval_base_url: str = Field(default="http://20.207.122.201", env="EVAL_BASE_URL")

    affordmed_email: str = Field(env="AFFORDMED_EMAIL")
    affordmed_name: str = Field(env="AFFORDMED_NAME")
    affordmed_mobile_no: str = Field(env="AFFORDMED_MOBILE_NO")
    affordmed_github_username: str = Field(env="AFFORDMED_GITHUB_USERNAME")
    affordmed_roll_no: str = Field(env="AFFORDMED_ROLL_NO")
    affordmed_access_code: str = Field(default="PTBMmQ", env="AFFORDMED_ACCESS_CODE")

    eval_client_id: str | None = Field(default=None, env="EVAL_CLIENT_ID")
    eval_client_secret: str | None = Field(default=None, env="EVAL_CLIENT_SECRET")

    class Config:
        case_sensitive = False


def get_settings() -> Settings:
    """
    Resolve settings from environment at runtime.
    """

    return Settings()
