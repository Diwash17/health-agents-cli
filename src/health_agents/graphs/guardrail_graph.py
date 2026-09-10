import json
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from health_agents.prompts.guardrail import DEFAULT_FAIL_MESSAGE, GUARDRAIL_SYSTEM_PROMPT


class GuardrailState(TypedDict):
    query: str
    passed: bool
    message: str


def build_guardrail_graph(llm: BaseChatModel) -> CompiledStateGraph:
    def check(state: GuardrailState) -> dict:
        messages = [
            SystemMessage(content=GUARDRAIL_SYSTEM_PROMPT),
            HumanMessage(content=state["query"]),
        ]
        response = llm.invoke(messages)
        return _parse_verdict(response.content)

    graph = StateGraph(GuardrailState)
    graph.add_node("check", check)
    graph.add_edge(START, "check")
    graph.add_edge("check", END)
    return graph.compile()


def _parse_verdict(raw: object) -> dict:
    text = str(raw).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Fail closed: if the gate's own response can't be parsed, we
        # can't confirm the query is safe, so treat it as not passed.
        return {"passed": False, "message": DEFAULT_FAIL_MESSAGE}

    passed = bool(data.get("passed", False))
    if passed:
        return {"passed": True, "message": ""}

    message = str(data.get("message") or "").strip() or DEFAULT_FAIL_MESSAGE
    return {"passed": False, "message": message}
