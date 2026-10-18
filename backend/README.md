# Model Proxy — Backend

An OpenAI Responses API proxy for Amazon Bedrock models, protected by an API Gateway API key. Clients pass the full Bedrock model or inference profile ID, for example `global.openai.gpt-6-luna`. The Lambda forwards only IDs listed in the stack's required `AllowedModelIds` parameter. Calls enter Bedrock through the stack Region (ap-south-1), and a `global.` profile may serve a request from any commercial Region.

## How It Works

```
client ──HTTPS──▶ CloudFront ──(+X-Origin-Verify)──▶ API Gateway REST (x-api-key, usage plan, STREAM)
                                                        │
                                                        ▼
                                  Lambda python3.14 + Lambda Web Adapter (response_stream)
                                                        │ SigV4 (Lambda role), model must be in ALLOWED_MODEL_IDS
                                                        ▼
                               bedrock-runtime.<stack Region> /openai/v1/responses  →  client's model ID
```

- One route: `POST /v1/responses`. The request `stream` field picks the mode. `true` returns Server-Sent Events, and `false` (the default) returns one JSON body.
- `model` is required. A request with a missing model or one that isn't on the allowlist gets a 400 before Bedrock is called.
- The model must support the Responses API on `bedrock-runtime`, which today means the OpenAI GPT models. Other models fail upstream.
- API Gateway enforces the API key, throttling (10 rps, burst 20) and a daily quota of 10,000 requests.
- CloudFront adds a secret `X-Origin-Verify` header, stored in Secrets Manager. The Lambda returns 403 when the header is missing, so calls made straight to the execute-api URL fail even with a valid key.
- IAM allows `bedrock:InvokeModel` on any model, provided the call enters Bedrock in the stack Region. Cross-Region routing is allowed only through inference profiles in that Region. The Lambda allowlist decides which models are actually reachable.

| File | Purpose |
|------|---------|
| `src/proxy/server.py` | HTTP handler: routing, origin check, stream/buffered relay |
| `src/proxy/request_policy.py` | Body validation, model allowlist, `stream` flag |
| `src/proxy/bedrock_responses.py` | SigV4-signed call to the bedrock-runtime Responses endpoint |
| `src/proxy/config.py` | Env vars (`ALLOWED_MODEL_IDS` and others) and constants |
| `src/run.sh` | Lambda handler started by Lambda Web Adapter |
| `template.yaml` | SAM stack: Lambda, REST API, API key, usage plan, CloudFront, secret |

## Prerequisites

- AWS SAM CLI 1.156 or later, AWS CLI v2, and uv with Python 3.14.
- Credentials for the target account, configured in your terminal.
- Access to each allowlisted model. Marketplace third-party models need their first invocation from a principal that can accept the Marketplace subscription.

## Deploy

```bash
cd model-proxy/backend
./scripts/deploy.sh --allowed-models global.openai.gpt-6-luna,us.openai.gpt-6-luna --region ap-south-1
for s in strands-agent langgraph-agent simple-api; do ./scripts/get-api-key.sh > ../samples/$s/.env; done
```

`--allowed-models` is required and has no default. To change the list, run the deploy again with a new value. After the first deploy, CloudFront takes about 5 minutes to go live.

## Test

```bash
uv run --python 3.14 pytest -q                      # local unit tests, no AWS calls
set -a; source ../samples/simple-api/.env; set +a
./scripts/smoke-test.sh                             # buffered, streaming, disallowed model (400), no key (403)
```

Example streaming call:

```bash
curl -N "$PROXY_BASE_URL/responses" -H "x-api-key: $PROXY_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"global.openai.gpt-6-luna","input":"Hello","stream":true}'
```

Logs go to the CloudWatch log group `/aws/lambda/model-proxy-proxy`.

## Limits

| Limit | Value | Where to change |
|-------|-------|-----------------|
| CloudFront origin response timeout (time to first byte, and the idle gap between bytes) | 60 s | `OriginReadTimeout`. Above 60 s needs a CloudFront quota increase |
| API Gateway integration timeout | 300 s | `IntegrationTimeoutMs` parameter |
| Lambda timeout | 300 s | `ProxyFunction.Timeout` |
| Request body | 10 MB | API Gateway limit |

Long buffered (`stream:false`) calls with high reasoning effort can hit the 60 s CloudFront limit. Use `stream:true` for those calls.

## License

MIT-0. See [LICENSE](../LICENSE). Developed and maintained by Irshad Chohan.
