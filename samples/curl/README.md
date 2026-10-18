# Model Proxy — curl

Calls the proxy with `curl`, with no SDK and no Python dependencies. The script uses `python3` only to escape the prompt into JSON. It sends the same prompt twice, once per mode of `POST /v1/responses`:

- `stream: false` returns one JSON response, printed raw.
- `stream: true` returns Server-Sent Events. `curl -N` prints each event as it arrives.

## Run

```bash
cd model-proxy/samples/curl
cp ../.env.example .env                          # then set PROXY_BASE_URL and PROXY_API_KEY
# or: ../../backend/scripts/get-api-key.sh > .env
./call.sh
./call.sh "What is a CloudFront origin request policy?"
```

## One-off commands

```bash
# Buffered
curl -sS "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" -H "x-api-key: $PROXY_API_KEY" \
  -d '{"model":"global.openai.gpt-6-luna","input":"Hello","stream":false}'

# Streaming
curl -sS -N "$PROXY_BASE_URL/responses" \
  -H "Content-Type: application/json" -H "x-api-key: $PROXY_API_KEY" \
  -d '{"model":"global.openai.gpt-6-luna","input":"Hello","stream":true}'
```

Load the variables first with `set -a; source .env; set +a`.

| Status | Meaning |
|--------|---------|
| 400 | Missing `input`, missing `model`, or a model that isn't on the allowlist |
| 403 | Missing or wrong `x-api-key`, or the call skipped CloudFront |
| 429 | Over the usage plan's throttle or daily quota |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROXY_BASE_URL` | Yes | `https://<distribution>.cloudfront.net/v1` (stack output `ProxyBaseUrl`) |
| `PROXY_API_KEY` | Yes | API Gateway key value |
| `MODEL_ID` | No | Full Bedrock model / inference profile ID. Default `global.openai.gpt-6-luna` |
| `REASONING_EFFORT` | No | `none`, `low`, `medium`, `high`, `xhigh` or `max`. Default `low` |
