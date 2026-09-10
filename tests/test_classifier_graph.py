from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from health_agents.graphs.classifier_graph import build_classifier_graph


def _classify(llm_response: str, query: str = "some query") -> str:
    llm = GenericFakeChatModel(messages=iter([llm_response]))
    graph = build_classifier_graph(llm)
    return graph.invoke({"query": query, "intent": ""})["intent"]


def test_classifies_summarize() -> None:
    assert _classify("summarize") == "summarize"


def test_classifies_synthesize() -> None:
    assert _classify("synthesize\n") == "synthesize"


def test_classifies_qna() -> None:
    assert _classify("qna") == "qna"


def test_unparseable_response_defaults_to_qna() -> None:
    assert _classify("I'm not sure what you mean") == "qna"
