#!/usr/bin/env bash
# Call the deployed proxy twice: buffered (stream=false) and streaming (stream=true).
# Requires PROXY_BASE_URL and PROXY_API_KEY (from ./scripts/get-api-key.sh).
set -euo pipefail

: "${PROXY_BASE_URL:?Set PROXY_BASE_URL (see scripts/get-api-key.sh)}"
: "${PROXY_API_KEY:?Set PROXY_API_KEY (see scripts/get-api-key.sh)}"

echo "== Buffered (stream=false) =="
curl --fail-with-body -sS --max-time 90 "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $PROXY_API_KEY" \
  -d '{"model":"gpt-6-luna","input":"Reply with exactly: proxy ok","reasoning":{"effort":"low"},"stream":false}'
echo

echo "== Streaming (stream=true) =="
curl --fail-with-body -sS -N --max-time 90 "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $PROXY_API_KEY" \
  -d '{"model":"gpt-6-luna","input":"Count from 1 to 5.","reasoning":{"effort":"low"},"stream":true}'
echo

echo "== Without API key (expect 403) =="
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 30 "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" -d '{"input":"hi"}'
