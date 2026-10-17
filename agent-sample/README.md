# Luna Proxy — Agent Sample

A Strands agent that calls GPT-6 Luna through the backend proxy. It uses `OpenAIResponsesModel` with `base_url` set to the CloudFront URL and the API Gateway key sent in the `x-api-key` header. No AWS credentials are needed on the client.

The agent has two local tools, `calculator` and `current_time`, which exercise the tool-calling round trip over the Responses API. Strands always streams, so these requests use `stream: true`.

## Run

```bash
cd luna-proxy/agent-sample
../backend/scripts/get-api-key.sh > .env      # or: cp .env.example .env and fill in values
uv sync
uv run agent.py                               # default prompt
uv run agent.py "What is 12.5% of 8,400?"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROXY_BASE_URL` | Yes | `https://<distribution>.cloudfront.net/v1` (stack output `ProxyBaseUrl`) |
| `PROXY_API_KEY` | Yes | API Gateway key value |
| `REASONING_EFFORT` | No | `none`, `low`, `medium`, `high`, `xhigh` or `max`. Default `low` |
