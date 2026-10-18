"""LangGraph agent that calls a Bedrock model through the CloudFront -> API Gateway proxy.

The graph is the standard tool loop: the model node either answers or requests tools,
the tool node runs them, and control returns to the model until it answers.

Run:  uv run agent.py "What is 17% of 2,340, and what time is it in Mumbai?"
"""

import ast
import operator
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

DEFAULT_PROMPT = "What is 17% of 2,340, and what time is it right now in Mumbai?"
DEFAULT_MODEL_ID = "global.openai.gpt-6-luna"
SYSTEM_PROMPT = "You are a concise assistant. Use tools for arithmetic and time lookups."
# The OpenAI SDK requires an api_key; auth is the API Gateway key in x-api-key instead.
UNUSED_OPENAI_KEY = "not-used-by-proxy"
ARITHMETIC_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


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


TOOLS = [calculator, current_time]


def build_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID),
        base_url=require_env("PROXY_BASE_URL"),
        api_key=UNUSED_OPENAI_KEY,
        default_headers={"x-api-key": require_env("PROXY_API_KEY")},
        use_responses_api=True,
        reasoning={"effort": os.environ.get("REASONING_EFFORT", "low")},
        streaming=True,
    )


def build_graph():
    model = build_model().bind_tools(TOOLS)

    def call_model(state: MessagesState) -> dict:
        return {"messages": [model.invoke([SystemMessage(SYSTEM_PROMPT), *state["messages"]])]}

    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", tools_condition)  # tools requested -> "tools", else END
    graph.add_edge("tools", "model")
    return graph.compile()


def main() -> None:
    load_dotenv()
    prompt = " ".join(sys.argv[1:]) or DEFAULT_PROMPT
    for update in build_graph().stream({"messages": [HumanMessage(prompt)]}, stream_mode="updates"):
        for node, output in update.items():
            for message in output["messages"]:
                for call in getattr(message, "tool_calls", []):
                    print(f"[{node}] tool call: {call['name']}({call['args']})")
                if message.type == "tool":
                    print(f"[{node}] {message.name} -> {message.content}")
                elif message.text:
                    print(f"[{node}] {message.text}")


if __name__ == "__main__":
    main()
