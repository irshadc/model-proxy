# Model Proxy

An API-key-protected proxy for Amazon Bedrock that exposes the OpenAI Responses API. Clients call one CloudFront URL with an API Gateway key and a full Bedrock model ID. They need no AWS credentials. Four samples show how to call it: Strands Agents, LangGraph, plain HTTP and curl.

## What It Does

- Gives teams and tools an OpenAI-compatible `POST /v1/responses` endpoint backed by Bedrock.
- Replaces per-user AWS credentials with API Gateway keys, with throttling and a daily quota per key.
- Limits callers to the Bedrock model IDs you allow when you deploy.
- Returns streaming (Server-Sent Events) or buffered JSON, chosen per request.

## Features

| Feature | Description |
|---------|-------------|
| OpenAI Responses API | `POST /v1/responses`, forwarded to the bedrock-runtime Responses endpoint |
| Model allowlist | Clients pass a full model ID. Only IDs in `AllowedModelIds` are forwarded |
| Streaming and buffered | `stream: true` returns SSE, and `stream: false` returns one JSON body |
| API key auth | API Gateway key in the `x-api-key` header, with a usage plan (10 rps, burst 20, 10,000 requests/day) |
| Origin lock | CloudFront adds a secret header, and calls that skip CloudFront get 403 |
| Region control | Bedrock is called in the stack Region. `global.` profiles may serve from any commercial Region |
| Keyless clients | The Lambda IAM role signs calls to Bedrock, so clients hold only the API key |
| Infrastructure as code | One SAM template plus deploy, key and smoke-test scripts |
| Samples | Strands Agents, LangGraph, a standard-library HTTP client and a curl script, each self-contained |

## How It Works

A client sends a Responses API request to CloudFront with its `x-api-key`. CloudFront adds a secret origin header and forwards the request to a Regional API Gateway REST API. API Gateway checks the key, applies the usage plan, and invokes the Lambda in response streaming mode.

The Lambda runs Python 3.14 behind Lambda Web Adapter. It checks the origin header and confirms the requested `model` is on the allowlist. It then signs the request with its IAM role and forwards it to `bedrock-runtime.<region>.amazonaws.com/openai/v1/responses`. Streaming responses are relayed chunk by chunk, and buffered responses are returned whole.

```
client ─▶ CloudFront ─▶ API Gateway (API key, usage plan) ─▶ Lambda (allowlist, SigV4) ─▶ Bedrock
```

See [backend/README.md](backend/README.md) for the component table, IAM and limits.

## Repository Layout

| Path | Type | Description |
|------|------|-------------|
| [backend/](backend/README.md) | API | SAM stack: CloudFront, API Gateway, Lambda proxy, tests, scripts |
| [samples/](samples/README.md) | Clients | Strands, LangGraph, plain HTTP and curl samples |

## Quick Start

```bash
cd model-proxy/backend
./scripts/deploy.sh --allowed-models global.openai.gpt-6-luna --region ap-south-1
./scripts/get-api-key.sh > ../samples/simple-api/.env
cd ../samples/simple-api && uv run --env-file .env api_call.py
```

## Test

- Locally: `cd backend && uv run --python 3.14 pytest -q`. This runs the unit tests and makes no AWS calls.
- After deploy: run `backend/scripts/smoke-test.sh`. It checks a buffered call, a streaming call, a disallowed model (expect 400) and a call with no key (expect 403).
- End to end: run any sample in [samples/](samples/README.md).

## Documentation

- [backend/README.md](backend/README.md): architecture, deployment, limits
- [samples/README.md](samples/README.md): sample overview and setup
- [samples/strands-agent/README.md](samples/strands-agent/README.md)
- [samples/langgraph-agent/README.md](samples/langgraph-agent/README.md)
- [samples/simple-api/README.md](samples/simple-api/README.md)
- [samples/curl/README.md](samples/curl/README.md)

## License

MIT-0. See [LICENSE](LICENSE).

## About Author

Developed and maintained by Irshad Chohan.
