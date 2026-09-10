from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from health_agents.prompts.synthesis import SYNTHESIS_SYSTEM_PROMPT
from health_agents.transcript import format_transcript


class SynthesisState(TypedDict):
    qa_history: list[dict[str, str]]
    report_text: str


def build_synthesis_graph(llm: BaseChatModel) -> CompiledStateGraph:
    def synthesize(state: SynthesisState) -> dict:
        transcript = format_transcript(state["qa_history"])
        messages = [
            SystemMessage(content=SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=transcript),
        ]
        response = llm.invoke(messages)
        return {"report_text": response.content}

    graph = StateGraph(SynthesisState)
    graph.add_node("synthesize", synthesize)
    graph.add_edge(START, "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()
