from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

STATE_PATH = Path("iac/state.json")


def _require_env(key: str) -> str:
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return v


def _require_int_env(key: str) -> int:
    v = _require_env(key)
    try:
        return int(v)
    except ValueError as e:
        raise RuntimeError(
            f"Environment variable {key} must be an integer. Got: {v}"
        ) from e


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_env(key: str) -> str | None:
    return os.getenv(key)


@dataclass(frozen=True, slots=True)
class Config:
    DELIVERY_STREAM_NAME: str
    PREFIX: str
    BUFFERING_SIZE: int
    BUFFERING_TIME: int
    REGION_NAME: str

    ROLE_NAME: str
    BUCKET_NAME: str
    LAMBDA_FUNCTION_NAME: str
    LAMBDA_RUNTIME: str
    LAMBDA_HANDLER: str
    LAMBDA_TIMEOUT: int
    LAMBDA_MEMORY_MB: int

    GLUE_DATABASE_NAME: str | None = None
    GLUE_TABLE_NAME: str | None = None

    @staticmethod
    def from_env() -> Config:
        return Config(
            DELIVERY_STREAM_NAME=_require_env("DELIVERY_STREAM_NAME"),
            PREFIX=_require_env("PREFIX"),
            BUFFERING_SIZE=_require_int_env("BUFFERING_SIZE"),
            BUFFERING_TIME=_require_int_env("BUFFERING_TIME"),
            REGION_NAME=_require_env("REGION_NAME"),
            ROLE_NAME=_require_env("ROLE_NAME"),
            BUCKET_NAME=_require_env("BUCKET_NAME"),
            LAMBDA_FUNCTION_NAME=_require_env("LAMBDA_FUNCTION_NAME"),
            LAMBDA_RUNTIME=_require_env("LAMBDA_RUNTIME"),
            LAMBDA_HANDLER=_require_env("LAMBDA_HANDLER"),
            LAMBDA_TIMEOUT=_require_int_env("LAMBDA_TIMEOUT"),
            LAMBDA_MEMORY_MB=_require_int_env("LAMBDA_MEMORY_MB"),
            GLUE_DATABASE_NAME=_optional_env("GLUE_DATABASE_NAME"),
            GLUE_TABLE_NAME=_optional_env("GLUE_TABLE_NAME"),
        )


@dataclass(frozen=True, slots=True)
class State:
    version: str = "1.0"
    ROLE_ARN: str | None = None
    BUCKET_ARN: str | None = None
    LAMBDA_ARN: str | None = None

    @staticmethod
    def load(path: Path = STATE_PATH) -> State:
        raw = _load_state(path)
        version = raw.get("version", "0.0")

        if version != State.version:
            raw = State._migrate(raw, version)

        return State(
            version=raw.get("version", State.version),
            ROLE_ARN=raw.get("ROLE_ARN"),
            BUCKET_ARN=raw.get("BUCKET_ARN"),
            LAMBDA_ARN=raw.get("LAMBDA_ARN"),
        )

    @staticmethod
    def _migrate(old_state: dict[str, Any], old_version: str) -> dict[str, Any]:
        migrated = old_state.copy()

        if old_version == "0.0":
            migrated["version"] = "1.0"

        return migrated

    def save(self, path: Path = STATE_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "ROLE_ARN": self.ROLE_ARN,
            "BUCKET_ARN": self.BUCKET_ARN,
            "LAMBDA_ARN": self.LAMBDA_ARN,
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True, slots=True)
class Runtime:
    config: Config
    state: State

    def require_role_arn(self) -> str:
        if not self.state.ROLE_ARN:
            raise RuntimeError("Missing ROLE_ARN in state.json")
        return self.state.ROLE_ARN

    def require_bucket_arn(self) -> str:
        if not self.state.BUCKET_ARN:
            raise RuntimeError("Missing BUCKET_ARN in state.json")
        return self.state.BUCKET_ARN

    def require_lambda_arn(self) -> str:
        if not self.state.LAMBDA_ARN:
            raise RuntimeError("Missing LAMBDA_ARN in state.json")
        return self.state.LAMBDA_ARN
