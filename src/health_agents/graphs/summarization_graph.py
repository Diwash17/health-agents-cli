from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from health_agents.prompts.summarization import SUMMARIZATION_SYSTEM_PROMPT


class SummarizationState(TypedDict):
    document_text: str
    summary: str


def build_summarization_graph(llm: BaseChatModel) -> CompiledStateGraph:
    def summarize(state: SummarizationState) -> dict:
        messages = [
            SystemMessage(content=SUMMARIZATION_SYSTEM_PROMPT),
            HumanMessage(
                content=f"<health_report>\n{state['document_text']}\n</health_report>"
            ),
        ]
        response = llm.invoke(messages)
        return {"summary": response.content}

    graph = StateGraph(SummarizationState)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "summarize")
    graph.add_edge("summarize", END)
    return graph.compile()
