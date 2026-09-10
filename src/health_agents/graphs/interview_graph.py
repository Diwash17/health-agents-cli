import json
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from health_agents.prompts.interview import (
    INTERVIEW_SYSTEM_PROMPT,
    MAX_QUESTIONS,
    MIN_QUESTIONS,
)
from health_agents.transcript import format_transcript

FALLBACK_QUESTION = "Can you tell me more about your symptoms?"


class InterviewState(TypedDict):
    qa_history: list[dict[str, str]]
    question_count: int
    question: str | None
    sufficient: bool


def build_interview_graph(llm: BaseChatModel) -> CompiledStateGraph:
    def decide(state: InterviewState) -> dict:
        count = state["question_count"]
        if count >= MAX_QUESTIONS:
            return {"sufficient": True, "question": None}

        transcript = format_transcript(state["qa_history"]) or "(no answers yet)"
        messages = [
            SystemMessage(content=INTERVIEW_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Questions asked so far: {count} "
                    f"(minimum {MIN_QUESTIONS}, maximum {MAX_QUESTIONS}).\n\n"
                    f"Conversation so far:\n{transcript}"
                )
            ),
        ]
        response = llm.invoke(messages)
        decision = _parse_decision(response.content)

        if count < MIN_QUESTIONS:
            return {"sufficient": False, "question": decision["question"]}
        if decision["sufficient"]:
            return {"sufficient": True, "question": None}
        return {"sufficient": False, "question": decision["question"]}

    graph = StateGraph(InterviewState)
    graph.add_node("decide", decide)
    graph.add_edge(START, "decide")
    graph.add_edge("decide", END)
    return graph.compile()


def _parse_decision(raw: object) -> dict:
    text = str(raw).strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else text

    try:
        data = json.loads(text)
        question = str(data.get("question") or "").strip() or None
        return {
            "sufficient": bool(data.get("sufficient", False)),
            "question": question or FALLBACK_QUESTION,
        }
    except (json.JSONDecodeError, AttributeError):
        return {"sufficient": False, "question": text or FALLBACK_QUESTION}
