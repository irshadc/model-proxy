# Model Proxy — Samples

Four clients for the model proxy, each self-contained with its own `pyproject.toml`, `uv.lock`, `README.md` and `.env`. They all call `POST /v1/responses` on the CloudFront URL with an API Gateway key. They need no AWS credentials.

| Sample | Approach | Key libraries | Stream mode |
|--------|----------|---------------|-------------|
| [strands-agent/](strands-agent/README.md) | Strands agent with two local tools | `strands-agents[openai]` 1.61.1 | `stream: true` |
| [langgraph-agent/](langgraph-agent/README.md) | LangGraph `StateGraph` tool loop | `langgraph` 1.2.16, `langchain-openai` 1.7.2 | `stream: true` |
| [simple-api/](simple-api/README.md) | Plain HTTP, no SDK | Python standard library (`urllib`) | `stream: false` and `stream: true` |
| [curl/](curl/README.md) | Shell script with curl | `curl` (`python3` only for JSON escaping) | `stream: false` and `stream: true` |

The two agent samples use the same `calculator` and `current_time` tools and the same default prompt, so you can compare their output directly.

## Setup

Each sample reads a `.env` in its own folder. Create one from the shared template [.env.example](.env.example):

```bash
cd model-proxy/samples/strands-agent
cp ../.env.example .env                          # then set PROXY_BASE_URL and PROXY_API_KEY
# or fill it from the deployed stack:
../../backend/scripts/get-api-key.sh > .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `PROXY_BASE_URL` | Yes | `https://<distribution>.cloudfront.net/v1` (stack output `ProxyBaseUrl`) |
| `PROXY_API_KEY` | Yes | API Gateway key value |
| `MODEL_ID` | No | Full Bedrock model / inference profile ID on the stack's allowlist. Default `global.openai.gpt-6-luna` |
| `REASONING_EFFORT` | No | `none`, `low`, `medium`, `high`, `xhigh` or `max`. Default `low` |

## Run

```bash
(cd strands-agent   && uv run agent.py)
(cd langgraph-agent && uv run agent.py)
(cd simple-api      && uv run --env-file .env api_call.py)
(cd curl            && ./call.sh)
```

The Python samples need Python 3.14 and uv. See [../backend/README.md](../backend/README.md) to deploy the proxy.

## License

MIT-0. See [LICENSE](../LICENSE).
