"""Strands agent that calls a Bedrock model through the CloudFront -> API Gateway proxy.

Run:  uv run agent.py "What is 17% of 2,340, and what time is it in Mumbai?"
"""

import ast
import operator
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from strands import Agent, tool
from strands.models.openai_responses import OpenAIResponsesModel

DEFAULT_PROMPT = "What is 17% of 2,340, and what time is it right now in Mumbai?"
ARITHMETIC_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
DEFAULT_MODEL_ID = "global.openai.gpt-6-luna"
# The OpenAI SDK requires an api_key; auth is the API Gateway key in x-api-key instead.
UNUSED_OPENAI_KEY = "not-used-by-proxy"


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name} (copy ../.env.example to .env)")
    return value


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression such as '0.17 * 2340'.

    Args:
        expression: Arithmetic using numbers, + - * / and parentheses.
    """
    try:
        return str(_evaluate(ast.parse(expression, mode="eval").body))
    except (SyntaxError, ValueError, ZeroDivisionError) as exc:
        return f"Cannot evaluate expression: {exc}"


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate(node.operand)
    if isinstance(node, ast.BinOp) and type(node.op) in ARITHMETIC_OPERATORS:
        return ARITHMETIC_OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
    raise ValueError("only numbers, + - * / and parentheses are allowed")


@tool
def current_time(timezone: str) -> str:
    """Return the current time in an IANA timezone such as 'Asia/Kolkata'.

    Args:
        timezone: IANA timezone name.
    """
    return datetime.now(ZoneInfo(timezone)).strftime("%Y-%m-%d %H:%M:%S %Z")


def build_agent() -> Agent:
    model = OpenAIResponsesModel(
        model_id=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID),
        client_args={
            "base_url": require_env("PROXY_BASE_URL"),
            "api_key": UNUSED_OPENAI_KEY,
            "default_headers": {"x-api-key": require_env("PROXY_API_KEY")},
        },
        params={"reasoning": {"effort": os.environ.get("REASONING_EFFORT", "low")}},
    )
    return Agent(
        model=model,
        tools=[calculator, current_time],
        system_prompt="You are a concise assistant. Use tools for arithmetic and time lookups.",
    )


def main() -> None:
    load_dotenv()
    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    result = build_agent()(prompt)
    print(f"\n\n--- stop_reason: {result.stop_reason}")


if __name__ == "__main__":
    main()
