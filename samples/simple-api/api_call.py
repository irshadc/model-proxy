"""Call the model proxy with plain HTTP (Python standard library only, no SDK).

Shows both modes of POST /v1/responses:
  stream=false -> one JSON response
  stream=true  -> Server-Sent Events, printed as text deltas arrive

Run:  uv run --env-file .env api_call.py "Explain CloudFront in one sentence."
"""

import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_PROMPT = "Explain Amazon CloudFront in one sentence."
DEFAULT_MODEL_ID = "global.openai.gpt-6-luna"
REQUEST_TIMEOUT_SECONDS = 60
SSE_DATA_PREFIX = "data: "
SSE_DONE_SENTINEL = "[DONE]"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name} (copy ../.env.example to .env)")
    return value


def post_responses(payload: dict) -> urllib.request.Request:
    return urllib.request.Request(
        f"{require_env('PROXY_BASE_URL')}/responses",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": require_env("PROXY_API_KEY"),
        },
    )


def output_text(response: dict) -> str:
    """Join the text parts of a Responses API result (skips reasoning items)."""
    return "".join(
        part["text"]
        for item in response.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )


def call_buffered(payload: dict) -> None:
    with urllib.request.urlopen(post_responses({**payload, "stream": False}),
                                timeout=REQUEST_TIMEOUT_SECONDS) as response:
        result = json.load(response)
    print(output_text(result))
    print(f"[usage] {result.get('usage', {})}")


def call_streaming(payload: dict) -> None:
    with urllib.request.urlopen(post_responses({**payload, "stream": True}),
                                timeout=REQUEST_TIMEOUT_SECONDS) as response:
        for raw_line in response:
            line = raw_line.decode().strip()
            if not line.startswith(SSE_DATA_PREFIX):
                continue
            data = line.removeprefix(SSE_DATA_PREFIX)
            if data == SSE_DONE_SENTINEL:
                break
            event = json.loads(data)
            if event["type"] == "response.output_text.delta":
                print(event["delta"], end="", flush=True)
            elif event["type"] == "response.completed":
                print(f"\n[usage] {event['response'].get('usage', {})}")


def main() -> None:
    payload = {
        "model": os.environ.get("MODEL_ID", DEFAULT_MODEL_ID),
        "input": " ".join(sys.argv[1:]) or DEFAULT_PROMPT,
        "reasoning": {"effort": os.environ.get("REASONING_EFFORT", "low")},
    }
    try:
        print("== Buffered (stream=false) ==")
        call_buffered(payload)
        print("\n== Streaming (stream=true) ==")
        call_streaming(payload)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Proxy returned HTTP {exc.code}: {exc.read().decode()}") from exc


if __name__ == "__main__":
    main()
