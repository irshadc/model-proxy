#!/usr/bin/env bash
# Call the deployed proxy: buffered, streaming, disallowed model (400) and no API key (403).
# Requires PROXY_BASE_URL and PROXY_API_KEY (from ./scripts/get-api-key.sh).
# MODEL_ID must be one of the stack's AllowedModelIds (default: global.openai.gpt-6-luna).
set -euo pipefail

: "${PROXY_BASE_URL:?Set PROXY_BASE_URL (see scripts/get-api-key.sh)}"
: "${PROXY_API_KEY:?Set PROXY_API_KEY (see scripts/get-api-key.sh)}"
MODEL_ID="${MODEL_ID:-global.openai.gpt-6-luna}"

call() {
  curl -sS -N --max-time 90 "$PROXY_BASE_URL/responses" \
    -H "Content-Type: application/json" -H "x-api-key: $PROXY_API_KEY" "$@"
}

echo "== Buffered (stream=false, model=$MODEL_ID) =="
call --fail-with-body \
  -d "{\"model\":\"$MODEL_ID\",\"input\":\"Reply with exactly: proxy ok\",\"reasoning\":{\"effort\":\"low\"},\"stream\":false}"
echo

echo "== Streaming (stream=true, model=$MODEL_ID) =="
call --fail-with-body \
  -d "{\"model\":\"$MODEL_ID\",\"input\":\"Count from 1 to 5.\",\"reasoning\":{\"effort\":\"low\"},\"stream\":true}"
echo

echo "== Model not on allowlist (expect 400) =="
call -o /dev/null -w "%{http_code}\n" -d '{"model":"not.an.allowed-model","input":"hi"}'

echo "== Without API key (expect 403) =="
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 30 "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" -d "{\"model\":\"$MODEL_ID\",\"input\":\"hi\"}"
