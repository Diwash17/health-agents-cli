from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from health_agents.graphs.guardrail_graph import build_guardrail_graph
from health_agents.prompts.guardrail import DEFAULT_FAIL_MESSAGE


def _invoke(llm_response: str, query: str = "What causes migraines?") -> dict:
    llm = GenericFakeChatModel(messages=iter([llm_response]))
    graph = build_guardrail_graph(llm)
    return graph.invoke({"query": query, "passed": False, "message": ""})


def test_passing_query_has_no_message() -> None:
    result = _invoke('{"passed": true, "message": "should be ignored"}')

    assert result["passed"] is True
    assert result["message"] == ""


def test_failing_query_returns_models_message() -> None:
    result = _invoke(
        '{"passed": false, "message": "Let\'s keep this to health topics."}'
    )

    assert result["passed"] is False
    assert result["message"] == "Let's keep this to health topics."


def test_failing_query_with_empty_message_uses_default() -> None:
    result = _invoke('{"passed": false, "message": ""}')

    assert result["passed"] is False
    assert result["message"] == DEFAULT_FAIL_MESSAGE


def test_malformed_response_fails_closed() -> None:
    result = _invoke("not json at all")

    assert result["passed"] is False
    assert result["message"] == DEFAULT_FAIL_MESSAGE
