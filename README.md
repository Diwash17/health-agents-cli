# health-agents

A CLI healthcare assistant built as a LangGraph pipeline, using Groq-hosted LLMs. It can summarize existing health reports, conduct patient interviews to generate new reports, and answer general health questions — all routed through an automated safety guardrail and intent classifier.

## Architecture

```
user query
        |
        v
  Input Guardrail node    -- rejects unsafe/harmful/injection/
        |                    off-domain queries; loops back on failure
        v (passed)
  Query Classifier node   -- routes to one of:
        |                      "summarize", "synthesize", "qna"
        v
  +-----------------+-----------------+
  |                 |                 |
  v                 v                 v
Summarization    Synthesis         QnA
agent             agent            agent
```

Each agent is its own LangGraph `StateGraph`. The guardrail and classifier are single-node graphs. The CLI orchestrates them in sequence and dispatches to the appropriate agent.

## Features

- **Summarization** — paste or upload a `.txt`/`.pdf` health report and get a 3-paragraph clinical summary
- **Synthesis** — interactive patient interview (6-10 adaptive questions) that generates a structured PDF health report
- **QnA** — general health chat with domain scoping, safety disclaimers, and emergency awareness
- **Input Guardrail** — safety gate that rejects harmful, injection, or off-domain queries before they reach any agent
- **Intent Classifier** — automatically routes queries to the right agent
- **Defense in depth** — multiple layers of safety: guardrail, per-agent prompt scoping, XML-delimited untrusted input, fail-closed parsing

## Tech Stack

- **uv** — dependency and virtual environment management
- **LangGraph** — each agent is a compiled `StateGraph`
- **langchain-groq** (`ChatGroq`) — LLM client via the Groq API
- **Typer + Rich** — CLI framework and terminal output formatting
- **pypdf** — PDF text extraction
- **fpdf2** — PDF report generation
- **pydantic-settings** — configuration from `.env`
- **pytest** — tests use `langchain_core` fake chat models (no real API calls)

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- A [Groq](https://groq.com/) API key

## Setup

```bash
# Clone the repository
git clone <repo-url>
cd new_project

# Create .env and add your Groq API key
cp .env.example .env
# Edit .env and fill in GROQ_API_KEY

# Install dependencies
uv sync
```

## Configuration

Each task uses a configurable Groq model, set via `.env` (see `.env.example`):

| Setting | Default | Purpose |
|---|---|---|
| `GROQ_MODEL_GUARDRAIL` | `openai/gpt-oss-safeguard-20b` | Safety/policy classification |
| `GROQ_MODEL_CLASSIFIER` | `openai/gpt-oss-20b` | Fast single-word routing |
| `GROQ_MODEL_SUMMARIZE` | `openai/gpt-oss-120b` | Clinical document reasoning |
| `GROQ_MODEL_SYNTHESIZE` | `openai/gpt-oss-120b` | Interview + report generation |
| `GROQ_MODEL_QNA` | `openai/gpt-oss-120b` | Conversational Q&A |

Available model IDs depend on your Groq account. Check what's enabled for your key with `Groq(api_key=...).models.list()`.

## Usage

```bash
# Main entrypoint — guardrail + classifier route your query automatically
uv run health-agents ask

# Standalone commands
uv run health-agents summarize --file path/to/report.pdf
uv run health-agents summarize              # paste text, Ctrl-D to finish
uv run health-agents synthesize             # interactive interview → PDF report
uv run health-agents qna                    # health chat loop (type 'exit' to quit)
```

### `ask` Command

The primary entrypoint. Type a query in natural language and the pipeline:

1. Runs it through the **input guardrail** — rejects unsafe or off-topic queries with a redirect message
2. **Classifies** the intent — routes to summarize, synthesize, or QnA
3. Dispatches to the appropriate agent flow

Type `exit` to quit.

### `summarize` Command

Summarizes an existing health report into 3 paragraphs:

- `--file` / `-f`: path to a `.txt` or `.pdf` file
- Omit `--file` to paste text directly (press Ctrl-D when done)

### `synthesize` Command

Conducts a structured patient interview (6-10 questions) and generates a PDF health report with sections:

- Chief Complaint
- History of Present Illness
- Relevant Medical History
- Current Medications and Allergies
- Assessment
- Recommendations

Options:

- `--output-dir` / `-o`: directory for the generated PDF (default: `reports/`)

### `qna` Command

General health Q&A chat. Greets on start, refuses off-domain questions, flags possible emergencies, and reminds users it provides general information only.

Type `exit` or `quit` to end the session.

## Project Structure

```
src/health_agents/
  cli.py                    # Typer app, one command per agent
  config.py                 # Settings (env-backed)
  llm.py                    # ChatGroq client factory
  transcript.py             # Q&A list -> plain text transcript
  io/
    document_loader.py      # .txt / .pdf -> plain text
    report_pdf.py           # report text -> PDF file (fpdf2)
  prompts/                  # system prompts, one module per agent
    summarization.py
    interview.py
    synthesis.py
    qna.py
    guardrail.py
    classifier.py
  graphs/                   # one StateGraph builder per agent
    summarization_graph.py
    interview_graph.py
    synthesis_graph.py
    qna_graph.py
    guardrail_graph.py
    classifier_graph.py
tests/                      # pytest tests with fake LLMs
docs/                       # prompting guides and examples
```

## Development

```bash
# Run tests
uv run pytest

# Run a specific test file
uv run pytest tests/test_guardrail_graph.py
```

Tests use `langchain_core.language_models.fake_chat_models` (`GenericFakeChatModel`) to avoid real network calls. Recording fake model subclasses capture messages sent to the LLM to verify prompt construction and safety properties.

## Safety

This project implements multiple layers of safety:

1. **Input Guardrail** — first line of defense; rejects harmful, injection, or completely off-domain queries
2. **Per-agent system prompts** — each agent independently enforces domain scope
3. **XML delimiters** — user-supplied document text is wrapped in `<health_report>` tags and treated as data only, not instructions
4. **Fail-closed parsing** — guardrail and classifier default to safe behavior on unparseable LLM output
5. **QnA domain guardrail** — independent of the input guardrail, the QnA agent restricts scope and resists role-change attempts

**Disclaimer:** This tool provides general health information only. It does not diagnose, prescribe, or replace a licensed healthcare professional.

## License

This project is provided as-is for educational and demonstration purposes.
