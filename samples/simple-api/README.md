# Model Proxy — Simple API Call

Calls the proxy with plain HTTP, using only the Python standard library (`urllib`), with no SDK and no dependencies. It sends the same prompt twice, once per mode of `POST /v1/responses`:

- `stream: false` returns one JSON response. The script prints the output text and token usage.
- `stream: true` returns Server-Sent Events. The script prints each `response.output_text.delta` as it arrives and stops at `data: [DONE]`.

Every request needs the `x-api-key` header and a `model` that is on the stack's allowlist. The model defaults to `global.openai.gpt-6-luna`.

## Run

```bash
cd model-proxy/samples/simple-api
../../backend/scripts/get-api-key.sh > .env     # or: cp .env.example .env and fill in values
uv run --env-file .env api_call.py
uv run --env-file .env api_call.py "Explain API Gateway usage plans in one sentence."
```

The same call with curl:

```bash
curl -N "$PROXY_BASE_URL/responses" -H "x-api-key: $PROXY_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"global.openai.gpt-6-luna","input":"Hello","stream":true}'
```

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
