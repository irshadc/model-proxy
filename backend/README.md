# Luna Proxy — Backend

An OpenAI Responses API proxy for GPT-6 Luna on Amazon Bedrock, protected by an API Gateway API key. All infrastructure lives in ap-south-1. Inference uses the global cross-Region profile `global.openai.gpt-6-luna`, so Bedrock may serve a request from any commercial Region.

## How It Works

```
client ──HTTPS──▶ CloudFront ──(+X-Origin-Verify)──▶ API Gateway REST (x-api-key, usage plan, STREAM)
                                                        │
                                                        ▼
                                  Lambda python3.14 + Lambda Web Adapter (response_stream)
                                                        │ SigV4 (Lambda role)
                                                        ▼
                     bedrock-runtime.ap-south-1 /openai/v1/responses  →  global.openai.gpt-6-luna
```

- One route: `POST /v1/responses`. The request `stream` field picks the mode. `true` returns Server-Sent Events, and `false` (the default) returns one JSON body.
- The proxy always replaces `model` with `global.openai.gpt-6-luna`, whatever the client sends.
- API Gateway enforces the API key, throttling (10 rps, burst 20) and a daily quota of 10,000 requests.
- CloudFront adds a secret `X-Origin-Verify` header, stored in Secrets Manager. The Lambda returns 403 when the header is missing, so calls made straight to the execute-api URL fail even with a valid key.
- The Lambda has no runtime dependencies beyond boto3, which the python3.14 runtime provides.

| File | Purpose |
|------|---------|
| `src/proxy/server.py` | HTTP handler: routing, origin check, stream/buffered relay |
| `src/proxy/request_policy.py` | Body validation, model pinning, `stream` flag |
| `src/proxy/bedrock_responses.py` | SigV4-signed call to the bedrock-runtime Responses endpoint |
| `src/proxy/config.py` | Env vars and constants |
| `src/run.sh` | Lambda handler started by Lambda Web Adapter |
| `template.yaml` | SAM stack: Lambda, REST API, API key, usage plan, CloudFront, secret |

## Prerequisites

- AWS SAM CLI 1.156 or later, AWS CLI v2, and uv with Python 3.14.
- Credentials for the target account, configured in your terminal.
- GPT-6 Luna enabled in the account. It is a Marketplace third-party model, so the first invocation must come from a principal that can accept the Marketplace subscription.

## Deploy

```bash
cd luna-proxy/backend
./scripts/deploy.sh --region ap-south-1            # optional: --stack-name luna-proxy --profile <name>
./scripts/get-api-key.sh > ../agent-sample/.env    # writes PROXY_BASE_URL and PROXY_API_KEY
```

Wait about 5 minutes after the first deploy for CloudFront to finish rolling out.

## Test

```bash
uv run --python 3.14 pytest -q                      # local unit tests, no AWS calls
set -a; source ../agent-sample/.env; set +a
./scripts/smoke-test.sh                             # buffered, streaming, and no-key (expect 403)
```

Example streaming call:

```bash
curl -N "$PROXY_BASE_URL/responses" -H "x-api-key: $PROXY_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-6-luna","input":"Hello","stream":true}'
```

Logs go to the CloudWatch log group `/aws/lambda/luna-proxy-proxy`.

## Limits

| Limit | Value | Where to change |
|-------|-------|-----------------|
| CloudFront origin response timeout (time to first byte, and the idle gap between bytes) | 60 s | `OriginReadTimeout`. Above 60 s needs a CloudFront quota increase |
| API Gateway integration timeout | 300 s | `IntegrationTimeoutMs` parameter |
| Lambda timeout | 300 s | `ProxyFunction.Timeout` |
| Request body | 10 MB | API Gateway limit |

Long buffered (`stream:false`) calls with high reasoning effort can hit the 60 s CloudFront limit. Use `stream:true` for those calls.
