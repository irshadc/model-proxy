#!/usr/bin/env bash
# Call the model proxy with curl: one buffered call and one streaming call.
# Usage: ./call.sh ["your prompt"]
# Reads PROXY_BASE_URL, PROXY_API_KEY and optional MODEL_ID / REASONING_EFFORT from ./.env.
set -euo pipefail

cd "$(dirname "$0")"
if [[ ! -f .env ]]; then
  echo "Missing .env: cp ../.env.example .env and set the values" >&2
  exit 1
fi
set -a; source .env; set +a

: "${PROXY_BASE_URL:?Set PROXY_BASE_URL in .env}"
: "${PROXY_API_KEY:?Set PROXY_API_KEY in .env}"
MODEL_ID="${MODEL_ID:-global.openai.gpt-6-luna}"
REASONING_EFFORT="${REASONING_EFFORT:-low}"
PROMPT="${1:-Explain Amazon API Gateway in one sentence.}"

# Build the JSON body safely (escapes quotes in the prompt).
body() {
  python3 -c 'import json,sys; print(json.dumps({"model": sys.argv[1], "input": sys.argv[2],
    "reasoning": {"effort": sys.argv[3]}, "stream": sys.argv[4] == "true"}))' \
    "$MODEL_ID" "$PROMPT" "$REASONING_EFFORT" "$1"
}

echo "== Buffered (stream=false, model=$MODEL_ID) =="
curl --fail-with-body -sS --max-time 60 "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $PROXY_API_KEY" \
  -d "$(body false)"
echo; echo

echo "== Streaming (stream=true, model=$MODEL_ID) =="
# -N disables curl buffering so Server-Sent Events print as they arrive.
curl --fail-with-body -sS -N --max-time 60 "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $PROXY_API_KEY" \
  -d "$(body true)"
echo
