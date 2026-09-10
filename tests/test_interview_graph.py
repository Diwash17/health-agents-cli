from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from health_agents.graphs.interview_graph import build_interview_graph


def test_forces_question_below_minimum_even_if_model_says_sufficient() -> None:
    llm = GenericFakeChatModel(
        messages=iter(['{"sufficient": true, "question": "Any allergies?"}'])
    )
    graph = build_interview_graph(llm)

    result = graph.invoke(
        {"qa_history": [], "question_count": 2, "question": None, "sufficient": False}
    )

    assert result["sufficient"] is False
    assert result["question"] == "Any allergies?"


def test_respects_model_sufficient_at_or_above_minimum() -> None:
    llm = GenericFakeChatModel(
        messages=iter(['{"sufficient": true, "question": ""}'])
    )
    graph = build_interview_graph(llm)

    result = graph.invoke(
        {"qa_history": [], "question_count": 6, "question": None, "sufficient": False}
    )

    assert result["sufficient"] is True
    assert result["question"] is None


def test_stops_at_maximum_without_calling_model() -> None:
    class ExplodingChatModel(GenericFakeChatModel):
        def invoke(self, *args, **kwargs):
            raise AssertionError("LLM should not be called once max is reached")

    llm = ExplodingChatModel(messages=iter([]))
    graph = build_interview_graph(llm)

    result = graph.invoke(
        {"qa_history": [], "question_count": 10, "question": None, "sufficient": False}
    )

    assert result["sufficient"] is True
    assert result["question"] is None


def test_falls_back_to_raw_text_on_malformed_json() -> None:
    llm = GenericFakeChatModel(messages=iter(["not json at all"]))
    graph = build_interview_graph(llm)

    result = graph.invoke(
        {"qa_history": [], "question_count": 7, "question": None, "sufficient": False}
    )

    assert result["sufficient"] is False
    assert result["question"] == "not json at all"
