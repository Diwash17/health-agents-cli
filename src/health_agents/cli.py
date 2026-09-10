import sys
from pathlib import Path

import typer
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from health_agents.config import get_settings
from health_agents.graphs.classifier_graph import build_classifier_graph
from health_agents.graphs.guardrail_graph import build_guardrail_graph
from health_agents.graphs.interview_graph import build_interview_graph
from health_agents.graphs.qna_graph import build_qna_graph
from health_agents.graphs.summarization_graph import build_summarization_graph
from health_agents.graphs.synthesis_graph import build_synthesis_graph
from health_agents.io.document_loader import load_document
from health_agents.io.report_pdf import write_report_pdf
from health_agents.llm import get_groq_chat

app = typer.Typer(help="Healthcare CLI assistant.")
console = Console()


def _run_summarize(llm: BaseChatModel, file: Path | None = None) -> None:
    if file is not None:
        document_text = load_document(file)
    else:
        console.print(
            "[bold]Paste the health report text[/bold] "
            "(press Ctrl-D when done):"
        )
        document_text = sys.stdin.read()

    if not document_text.strip():
        console.print("[red]No input provided.[/red]")
        return

    graph = build_summarization_graph(llm)
    result = graph.invoke({"document_text": document_text, "summary": ""})
    console.print(Panel(result["summary"], title="Summary", border_style="green"))


def _run_synthesize(llm: BaseChatModel, output_dir: Path) -> None:
    interview_graph = build_interview_graph(llm)
    synthesis_graph = build_synthesis_graph(llm)

    console.print(
        "[bold]I'll ask a few questions to put together your health "
        "report.[/bold]"
    )

    qa_history: list[dict[str, str]] = []
    question_count = 0
    while True:
        decision = interview_graph.invoke(
            {
                "qa_history": qa_history,
                "question_count": question_count,
                "question": None,
                "sufficient": False,
            }
        )
        if decision["sufficient"] or not decision["question"]:
            break

        question = decision["question"]
        console.print(f"\n[cyan]Q{question_count + 1}.[/cyan] {question}")
        answer = Prompt.ask("Your answer")
        qa_history.append({"question": question, "answer": answer})
        question_count += 1

    if not qa_history:
        console.print("[red]No answers collected; cannot generate a report.[/red]")
        return

    console.print("\n[bold]Generating your health report...[/bold]")
    result = synthesis_graph.invoke({"qa_history": qa_history, "report_text": ""})
    pdf_path = write_report_pdf(result["report_text"], output_dir)

    console.print(
        Panel(
            f"Report saved to [green]{pdf_path}[/green]",
            title="Done",
            border_style="green",
        )
    )


def _run_qna(llm: BaseChatModel, opening_query: str | None = None) -> None:
    graph = build_qna_graph(llm)
    messages: list[BaseMessage] = []

    if opening_query is not None:
        messages.append(HumanMessage(content=opening_query))

    result = graph.invoke({"messages": messages, "response": ""})
    console.print(Panel(result["response"], title="Assistant", border_style="blue"))
    messages.append(AIMessage(content=result["response"]))

    while True:
        user_input = Prompt.ask("\n[bold]You[/bold]")
        if user_input.strip().lower() in {"exit", "quit"}:
            break

        messages.append(HumanMessage(content=user_input))
        result = graph.invoke({"messages": messages, "response": ""})
        console.print(Panel(result["response"], title="Assistant", border_style="blue"))
        messages.append(AIMessage(content=result["response"]))


@app.command()
def summarize(
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        exists=True,
        readable=True,
        help="Path to a .txt or .pdf health report. Omit to paste text instead.",
    ),
) -> None:
    """Summarize a health report into 3 paragraphs."""
    settings = get_settings()
    _run_summarize(get_groq_chat(settings.groq_model_summarize), file=file)


@app.command()
def synthesize(
    output_dir: Path = typer.Option(
        Path("reports"),
        "--output-dir",
        "-o",
        help="Directory to save the generated PDF report in.",
    ),
) -> None:
    """Interview the patient and generate a synthesized health report PDF."""
    settings = get_settings()
    _run_synthesize(get_groq_chat(settings.groq_model_synthesize), output_dir=output_dir)


@app.command()
def qna() -> None:
    """Chat with the general health Q&A assistant. Type 'exit' to quit."""
    settings = get_settings()
    _run_qna(get_groq_chat(settings.groq_model_qna))


@app.command()
def ask(
    output_dir: Path = typer.Option(
        Path("reports"),
        "--output-dir",
        "-o",
        help="Directory to save any generated PDF report in.",
    ),
) -> None:
    """Ask anything - routed automatically to the right agent. Type 'exit' to quit."""
    settings = get_settings()
    guardrail_graph = build_guardrail_graph(get_groq_chat(settings.groq_model_guardrail))
    classifier_graph = build_classifier_graph(get_groq_chat(settings.groq_model_classifier))

    console.print(
        "[bold]What do you need help with?[/bold] Describe your request "
        "in your own words - paste multi-line text if you like. Type "
        "'exit' to quit."
    )

    while True:
        console.print()
        query = Prompt.ask("[bold]You[/bold]")
        if query.strip().lower() in {"exit", "quit"}:
            break
        if not query.strip():
            continue

        guard_result = guardrail_graph.invoke(
            {"query": query, "passed": False, "message": ""}
        )
        if not guard_result["passed"]:
            console.print(
                Panel(
                    guard_result["message"],
                    title="Let's try again",
                    border_style="yellow",
                )
            )
            continue

        classification = classifier_graph.invoke({"query": query, "intent": ""})
        intent = classification["intent"]
        console.print(f"[dim]Routing to: {intent}[/dim]")

        if intent == "summarize":
            _run_summarize(get_groq_chat(settings.groq_model_summarize))
        elif intent == "synthesize":
            _run_synthesize(
                get_groq_chat(settings.groq_model_synthesize), output_dir=output_dir
            )
        else:
            _run_qna(get_groq_chat(settings.groq_model_qna), opening_query=query)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
