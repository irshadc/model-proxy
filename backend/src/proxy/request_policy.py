"""Validates client requests and rewrites them for Bedrock. No HTTP or AWS calls here."""

import hmac
import json
from dataclasses import dataclass


class InvalidRequest(ValueError):
    """Client sent a request the proxy will not forward (maps to HTTP 400)."""


@dataclass(frozen=True)
class ResponsesRequest:
    body: bytes
    is_streaming: bool


def is_trusted_origin(presented_secret: str | None, expected_secret: str) -> bool:
    """True when the request carries the secret header that only CloudFront adds."""
    if not presented_secret:
        return False
    return hmac.compare_digest(presented_secret.encode(), expected_secret.encode())


def build_responses_request(raw_body: bytes, allowed_model_ids: frozenset[str]) -> ResponsesRequest:
    """Parse the client body, check `model` against the allowlist, and read `stream`.

    The client must name a full Bedrock model or inference profile ID
    (e.g. global.openai.gpt-6-luna); anything not on the allowlist is rejected.
    """
    try:
        payload = json.loads(raw_body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRequest("Request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise InvalidRequest("Request body must be a JSON object")
    if "input" not in payload:
        raise InvalidRequest("Request body must include 'input'")

    stream_flag = payload.get("stream", False)
    if not isinstance(stream_flag, bool):
        raise InvalidRequest("'stream' must be true or false")

    model_id = payload.get("model")
    if not isinstance(model_id, str) or not model_id:
        raise InvalidRequest("Request body must include 'model' (a Bedrock model ID)")
    if model_id not in allowed_model_ids:
        raise InvalidRequest(f"Model '{model_id}' is not allowed on this proxy")

    return ResponsesRequest(body=raw_body, is_streaming=stream_flag)
