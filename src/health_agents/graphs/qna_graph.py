from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from health_agents.prompts.qna import QNA_SYSTEM_PROMPT


class QnAState(TypedDict):
    messages: list[BaseMessage]
    response: str


def build_qna_graph(llm: BaseChatModel) -> CompiledStateGraph:
    def respond(state: QnAState) -> dict:
        messages = [SystemMessage(content=QNA_SYSTEM_PROMPT), *state["messages"]]
        response = llm.invoke(messages)
        return {"response": response.content}

    graph = StateGraph(QnAState)
    graph.add_node("respond", respond)
    graph.add_edge(START, "respond")
    graph.add_edge("respond", END)
    return graph.compile()
