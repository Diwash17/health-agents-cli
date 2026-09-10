from types import SimpleNamespace

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from typer.testing import CliRunner

from health_agents.cli import app

runner = CliRunner()

FAKE_SETTINGS = SimpleNamespace(
    groq_model_guardrail="fake-guardrail-model",
    groq_model_classifier="fake-classifier-model",
    groq_model_summarize="fake-summarize-model",
    groq_model_synthesize="fake-synthesize-model",
    groq_model_qna="fake-qna-model",
)


def _patch_llm(monkeypatch, fake_llm: GenericFakeChatModel) -> None:
    monkeypatch.setattr("health_agents.cli.get_settings", lambda: FAKE_SETTINGS)
    monkeypatch.setattr(
        "health_agents.cli.get_groq_chat", lambda model, **kwargs: fake_llm
    )


def test_ask_routes_a_passing_health_query_to_qna(monkeypatch) -> None:
    fake_llm = GenericFakeChatModel(
        messages=iter(
            [
                '{"passed": true, "message": ""}',  # guardrail check
                "qna",  # classifier decision
                "Rest and hydrate; see a doctor if it persists.",  # qna reply
            ]
        )
    )
    _patch_llm(monkeypatch, fake_llm)

    result = runner.invoke(
        app,
        ["ask"],
        input="I have a headache, what should I do?\nexit\nexit\n",
    )

    assert result.exit_code == 0
    assert "Routing to: qna" in result.stdout
    assert "Rest and hydrate" in result.stdout


def test_ask_uses_the_task_specific_model_for_each_step(monkeypatch) -> None:
    fake_llm = GenericFakeChatModel(
        messages=iter(
            [
                '{"passed": true, "message": ""}',
                "qna",
                "General health information.",
            ]
        )
    )
    requested_models: list[str] = []

    monkeypatch.setattr("health_agents.cli.get_settings", lambda: FAKE_SETTINGS)
    monkeypatch.setattr(
        "health_agents.cli.get_groq_chat",
        lambda model, **kwargs: (requested_models.append(model), fake_llm)[1],
    )

    runner.invoke(app, ["ask"], input="I feel dizzy, any advice?\nexit\nexit\n")

    assert requested_models == [
        FAKE_SETTINGS.groq_model_guardrail,
        FAKE_SETTINGS.groq_model_classifier,
        FAKE_SETTINGS.groq_model_qna,
    ]


def test_ask_reprompts_on_failed_guardrail_without_routing(monkeypatch) -> None:
    fake_llm = GenericFakeChatModel(
        messages=iter(
            [
                '{"passed": false, "message": "Let\'s keep this to health topics."}',
            ]
        )
    )
    _patch_llm(monkeypatch, fake_llm)

    result = runner.invoke(app, ["ask"], input="what's today's weather?\nexit\n")

    assert result.exit_code == 0
    assert "Let's keep this to health topics." in result.stdout
    assert "Routing to:" not in result.stdout
