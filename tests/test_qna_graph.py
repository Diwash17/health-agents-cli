from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage

from health_agents.graphs.qna_graph import build_qna_graph


def test_empty_history_still_gets_a_response_for_greeting() -> None:
    llm = GenericFakeChatModel(messages=iter(["Hi, I'm your health assistant."]))
    graph = build_qna_graph(llm)

    result = graph.invoke({"messages": [], "response": ""})

    assert result["response"] == "Hi, I'm your health assistant."


def test_system_prompt_enforces_off_domain_guardrail() -> None:
    captured: list = []

    class RecordingFakeChatModel(GenericFakeChatModel):
        def invoke(self, messages, *args, **kwargs):
            captured.append(messages)
            return super().invoke(messages, *args, **kwargs)

    llm = RecordingFakeChatModel(messages=iter(["I can only help with health topics."]))
    graph = build_qna_graph(llm)

    graph.invoke(
        {
            "messages": [HumanMessage(content="Write me a Python quicksort function")],
            "response": "",
        }
    )

    system_message = captured[0][0]
    assert "politely decline" in system_message.content.lower()
    assert "only discuss health" in system_message.content.lower()


def test_conversation_history_is_threaded_through() -> None:
    captured: list = []

    class RecordingFakeChatModel(GenericFakeChatModel):
        def invoke(self, messages, *args, **kwargs):
            captured.append(messages)
            return super().invoke(messages, *args, **kwargs)

    llm = RecordingFakeChatModel(messages=iter(["follow-up answer"]))
    graph = build_qna_graph(llm)

    history = [
        HumanMessage(content="What helps with a mild headache?"),
        AIMessage(content="Rest, hydration, and over-the-counter pain relief can help."),
        HumanMessage(content="How much water should I drink?"),
    ]
    graph.invoke({"messages": history, "response": ""})

    sent = captured[0]
    assert len(sent) == 4  # system + 3 history messages
    assert sent[1:] == history
