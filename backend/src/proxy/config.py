"""Runtime settings. Required values come from env vars and fail fast when missing."""

import os
from dataclasses import dataclass

RESPONSES_PATH = "/v1/responses"
HEALTH_PATH = "/healthz"
ORIGIN_VERIFY_HEADER = "x-origin-verify"
MAX_REQUEST_BYTES = 10 * 1024 * 1024  # API Gateway REST payload limit
UPSTREAM_READ_CHUNK_BYTES = 8192
UPSTREAM_TIMEOUT_SECONDS = 290  # stays under the 300 s Lambda timeout


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def parse_model_allowlist(raw: str) -> frozenset[str]:
    """Split a comma-separated list of Bedrock model / inference profile IDs."""
    model_ids = frozenset(item.strip() for item in raw.split(",") if item.strip())
    if not model_ids:
        raise RuntimeError("ALLOWED_MODEL_IDS must list at least one model ID")
    return model_ids


@dataclass(frozen=True)
class Settings:
    port: int
    region: str
    allowed_model_ids: frozenset[str]
    origin_secret_arn: str

    @property
    def bedrock_host(self) -> str:
        return f"bedrock-runtime.{self.region}.amazonaws.com"


def load_settings() -> Settings:
    return Settings(
        port=int(_require("PORT")),
        region=_require("AWS_REGION"),
        allowed_model_ids=parse_model_allowlist(_require("ALLOWED_MODEL_IDS")),
        origin_secret_arn=_require("ORIGIN_SECRET_ARN"),
    )
