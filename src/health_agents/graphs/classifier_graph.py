from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from health_agents.prompts.classifier import (
    CLASSIFIER_SYSTEM_PROMPT,
    DEFAULT_INTENT,
    VALID_INTENTS,
)


class ClassificationState(TypedDict):
    query: str
    intent: str


def build_classifier_graph(llm: BaseChatModel) -> CompiledStateGraph:
    def classify(state: ClassificationState) -> dict:
        messages = [
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=state["query"]),
        ]
        response = llm.invoke(messages)
        return {"intent": _parse_intent(response.content)}

    graph = StateGraph(ClassificationState)
    graph.add_node("classify", classify)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", END)
    return graph.compile()


def _parse_intent(raw: object) -> str:
    text = str(raw).strip().lower()
    for intent in VALID_INTENTS:
        if intent in text:
            return intent
    return DEFAULT_INTENT
