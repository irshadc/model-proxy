# Model Proxy — LangGraph Agent

A LangGraph agent that calls a Bedrock model through the backend proxy. It uses `ChatOpenAI` from `langchain-openai` with `use_responses_api=True`, `base_url` set to the CloudFront URL, and the API Gateway key sent in the `x-api-key` header. No AWS credentials are needed on the client. The model defaults to `global.openai.gpt-6-luna`. Set `MODEL_ID` to use any other ID on the stack's allowlist.

The graph is an explicit `StateGraph` tool loop. A `model` node either answers or requests tools, a `ToolNode` runs the `calculator` and `current_time` tools, and control returns to `model` until it answers. Calls use `stream: true`.

## Run

```bash
cd model-proxy/samples/langgraph-agent
../../backend/scripts/get-api-key.sh > .env     # or: cp ../.env.example .env and set the values
uv sync
uv run agent.py                               # default prompt
uv run agent.py "What is 12.5% of 8,400?"
```

Sample output:

```
[model] tool call: calculator({'expression': '0.17 * 2340'})
[model] tool call: current_time({'timezone': 'Asia/Kolkata'})
[tools] calculator -> 397.8
[tools] current_time -> 2026-10-18 06:36:07 IST
[model] 17% of 2,340 is **397.8**. The time in Mumbai is **6:36 AM IST** on October 18, 2026.
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PROXY_BASE_URL` | Yes | `https://<distribution>.cloudfront.net/v1` (stack output `ProxyBaseUrl`) |
| `PROXY_API_KEY` | Yes | API Gateway key value |
| `MODEL_ID` | No | Full Bedrock model / inference profile ID. Default `global.openai.gpt-6-luna` |
| `REASONING_EFFORT` | No | `none`, `low`, `medium`, `high`, `xhigh` or `max`. Default `low` |
