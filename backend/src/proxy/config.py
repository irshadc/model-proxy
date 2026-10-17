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


@dataclass(frozen=True)
class Settings:
    port: int
    region: str
    model_id: str
    origin_secret_arn: str

    @property
    def bedrock_host(self) -> str:
        return f"bedrock-runtime.{self.region}.amazonaws.com"


def load_settings() -> Settings:
    return Settings(
        port=int(_require("PORT")),
        region=_require("AWS_REGION"),
        model_id=_require("MODEL_ID"),
        origin_secret_arn=_require("ORIGIN_SECRET_ARN"),
    )
