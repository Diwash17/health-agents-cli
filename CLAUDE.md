# health_agents

A CLI healthcare assistant built as a LangGraph pipeline, using Groq-hosted
LLMs. Input can be pasted multi-line text, a `.txt` file, or a `.pdf` file.

## Architecture

The full pipeline, entered via `uv run health-agents ask`:

```
user query (free text typed at the `ask` prompt)
        |
        v
  Input Guardrail node    -- LLM call; rejects unsafe/harmful/injection/
        |                    clearly non-healthcare queries. On failure,
        |                    shows the model's own clarify-and-retry
        |                    message and loops back for another query
        |                    (does NOT hard-exit the CLI).
        v (passed)
  Query Contextualizer /
  Classifier node          -- LLM call that routes to exactly one of:
        |                      "summarize", "synthesize", "qna"
        v
  +-----------------+-----------------+
  |                 |                 |
  v                 v                 v
Summarization    Synthesis         QnA
agent (graph)     agent (graph)    agent (graph)
  |                 |                 |
  (prompts for      (runs its own     (uses the query that
   file/paste,       6-10 question    triggered classification
   like the          interview,       as its first turn, then
   standalone        writes a PDF)    keeps chatting)
   command)
```

Each agent is its own small LangGraph `StateGraph`. The guardrail and
classifier are two more small single-node graphs. `ask` in `cli.py` is
the plain-Python orchestrator that invokes them in sequence and routes to
whichever agent's flow function the classifier picked — see "Orchestration
design notes" below for why this isn't one big combined graph.

## Build status

- [x] Project scaffold (this file, `pyproject.toml`, config, CLI shell)
- [x] Summarization agent (`summarize` command)
- [x] Synthesis agent (`synthesize` command) — interviews the patient
      (6-10 adaptive questions), then writes a PDF health report
- [x] QnA agent (`qna` command) — general health chat, greets on start,
      refuses off-domain questions via its own system prompt
- [x] Input guardrail node + query classifier, wired end-to-end as
      `ask` — the full pipeline described at the top of this file

### Synthesis agent design notes

Two small graphs, orchestrated by the CLI (not a single interrupt-driven
graph — see why below):

- `graphs/interview_graph.py` — one `decide` node, called once per
  question. Given the Q&A transcript so far and how many questions have
  been asked, the LLM returns strict JSON `{"sufficient": bool,
  "question": str}`. Code (not the LLM) enforces the bounds: always ask
  below `MIN_QUESTIONS` (6), always stop at `MAX_QUESTIONS` (10) without
  even calling the LLM, and only trust the LLM's `sufficient` flag in
  between. This is what makes the number of questions genuinely adapt
  per conversation instead of being fixed or arbitrarily cut short.
- `graphs/synthesis_graph.py` — one `synthesize` node that turns the
  full transcript into the final report text (fixed section headers:
  Chief Complaint, History of Present Illness, Relevant Medical History,
  Current Medications and Allergies, Assessment, Recommendations).
- `io/report_pdf.py` — pure rendering (no LLM), turns the report text
  into a PDF via `fpdf2`, bolding recognized section headers.
- The CLI (`synthesize` command in `cli.py`) drives the actual turn-by-turn
  loop: invoke `interview_graph` -> print question -> read one answer via
  `rich.prompt.Prompt.ask` -> append to history -> repeat.

We deliberately did **not** use LangGraph's `interrupt()`/human-in-the-loop
primitive for this loop: code that runs before an `interrupt()` call inside
a node re-executes on every resume, which would re-invoke the LLM and could
produce a different question than the one the user already answered. For a
single-process CLI session, driving the loop from the CLI with small,
stateless per-turn graph calls is simpler and avoids that footgun. If this
ever needs to survive process restarts (e.g. resume an interview later),
revisit `interrupt()` + a persistent checkpointer then.

### QnA agent design notes

`graphs/qna_graph.py` — one `respond` node, called once per turn. The
CLI (`qna` command) threads the running `list[BaseMessage]` conversation
history through each call (same stateless-per-turn pattern as the
interview agent, for the same reason: simpler, no interrupt-replay
footgun). All behavior — greeting, domain scope, safety disclaimers,
tone — lives in one detailed system prompt (`prompts/qna.py`), not in
code:

- **Greeting**: the CLI invokes the graph once before reading any user
  input, with an empty history. The system prompt instructs the model to
  open with a greeting only when there's no prior user message, and not
  to repeat it on later turns.
- **Off-domain guardrail**: the system prompt explicitly restricts scope
  to health/wellness topics, instructs the model to politely decline and
  redirect for anything else, and to ignore attempts (in the user's
  message) to override these instructions or change its role. This is
  the QnA agent's own defense, independent of and in addition to the
  project-wide Input Guardrail node (below) — defense in depth.
- **Safety**: instructs the model to flag possible emergencies and to
  remind the user it gives general information, not personalized medical
  advice.

### Orchestration design notes (`ask`, guardrail, classifier)

- `graphs/guardrail_graph.py` — one `check` node. Sends the raw query to
  the LLM with `prompts/guardrail.py`'s system prompt and expects strict
  JSON: `{"passed": bool, "message": str}`. Only fails closed on genuinely
  unsafe/injection/completely-off-domain content — sensitive-but-legitimate
  health topics (mental health, sexual health, substance use, etc.) are
  explicitly instructed to pass. On failure the model itself writes a
  short, kind redirect message (not a canned refusal) which `ask` shows
  before looping back to ask another query. If the LLM's response fails
  to parse as JSON, the graph **fails closed** (treats it as not passed)
  rather than silently letting an unparseable/unverified query through.
- `graphs/classifier_graph.py` — one `classify` node. Only runs after the
  guardrail passes. Asks the LLM to output exactly one word
  (`summarize` / `synthesize` / `qna`) per the criteria in
  `prompts/classifier.py`; unparseable output defaults to `qna` (the
  safest catch-all — a general chat response is the least likely to do
  something the user didn't ask for).
  - Found during live testing: phrasing like "I want a *summary* of what
    tests to track for my visit" was misrouted to `qna` even with no
    existing document, because the word "summary" pattern-matched
    toward `summarize`. The prompt's decision boundary is explicitly
    "does a document already exist" (not "does the word 'summary'
    appear"), reinforced with worked examples covering that exact case.
    Verified 9/9 on a hand-built accuracy check against the live model
    after the fix - re-run a check like that against `prompts/classifier.py`
    if you edit it again.
- `ask` in `cli.py` calls guardrail then classifier then dispatches to
  `_run_summarize` / `_run_synthesize` / `_run_qna` — the same flow
  functions the standalone `summarize`/`synthesize`/`qna` commands use, so
  there's one implementation of each agent's interactive behavior. For
  `qna`, the query that triggered classification is passed in as
  `opening_query` so it's answered directly instead of being asked again.
- This mirrors the earlier decision **not** to build one big
  interrupt-driven mega-graph: guardrail and classifier are each a single
  stateless LLM call (no loop, no human-in-the-loop concern), so they're
  graphs on their own merit. The parts that need real back-and-forth with
  a human (the interview, the chat) still live in plain CLI loops calling
  small stateless graphs turn-by-turn, for the reasons explained above.

Build one piece at a time, per direction from the project owner. Don't
assume unimplemented pieces exist.

## Tech stack

- **uv** — dependency/venv management (`uv add`, `uv run`)
- **LangGraph** — each agent is a compiled `StateGraph`
- **langchain-groq** (`ChatGroq`) — LLM client, talks to the Groq API
- **Typer + Rich** — CLI framework and terminal output formatting
- **pypdf** — `.pdf` text extraction
- **pydantic-settings** — loads `GROQ_API_KEY` and per-task model names
  from `.env` (see `config.py`)
- **pytest** — tests use `langchain_core`'s fake chat models to avoid
  real network calls; see `tests/`

Each task gets its own configurable model (`config.py`, overridable via
`.env` — see `.env.example`), not one shared default:

| Setting | Default | Why |
|---|---|---|
| `GROQ_MODEL_GUARDRAIL` | `openai/gpt-oss-safeguard-20b` | a safety/policy-classification-tuned model — a better fit for a pass/fail safety gate than a general chat model |
| `GROQ_MODEL_CLASSIFIER` | `openai/gpt-oss-20b` | single-word routing decision, runs on every query — fast/cheap matters |
| `GROQ_MODEL_SUMMARIZE` | `openai/gpt-oss-120b` | needs real reasoning quality over a clinical document |
| `GROQ_MODEL_SYNTHESIZE` | `openai/gpt-oss-120b` | both the interview questions and the final report need clinical judgment |
| `GROQ_MODEL_QNA` | `openai/gpt-oss-120b` | open-ended conversational answers, quality matters |

**Available model ids are account-specific** — Groq gates model access
per API key/org (verified while wiring this up: the initial
`llama-3.x` defaults 404'd as "does not exist or you do not have access
to it" on this project's key, even though those ids are broadly
documented). Check what's actually enabled for your key before assuming
a model id works: `Groq(api_key=...).models.list()`, or `uv run
health-agents ask` and read the error if a call 404s. `openai/gpt-oss-*`
models also emit hidden chain-of-thought in a separate `reasoning` field
on the response (not mixed into `content`) — irrelevant to our code since
we only read `.content` and never set `max_tokens`, but worth knowing if
you inspect raw responses and `content` looks unexpectedly short.

`llm.py`'s `get_groq_chat(model, temperature=0.2)` takes `model` as a
required argument on purpose — every call site must explicitly say which
task's model it wants, rather than silently sharing one implicit default.
`cli.py` builds a fresh `ChatGroq` instance per task from
`get_settings().groq_model_<task>` at each command/branch.

## Layout

```
src/health_agents/
  cli.py                          # Typer app, one command per agent
  config.py                       # Settings (env-backed)
  llm.py                          # ChatGroq client factory
  transcript.py                   # Q&A list -> plain text transcript
  io/document_loader.py           # .txt / .pdf -> plain text
  io/report_pdf.py                # report text -> PDF file (fpdf2)
  prompts/                        # system prompts, one module per agent
  graphs/                         # one StateGraph builder per agent
tests/
```

## Conventions

- Any text that came from a user-supplied document is untrusted input:
  wrap it in an explicit delimiter (e.g. `<health_report>...</health_report>`)
  in the prompt, and instruct the model explicitly to treat it as data,
  not instructions — this is how the summarization agent avoids acting on
  prompt injection or off-domain content embedded in an uploaded report.
  Apply the same pattern in the synthesis and QnA agents.
- Each agent gets its own prompt module under `prompts/` and its own
  graph module under `graphs/`, mirroring `summarization.py` /
  `summarization_graph.py`.
- Tests for graph wiring/prompt behavior use
  `langchain_core.language_models.fake_chat_models` (`GenericFakeChatModel`)
  instead of hitting the real Groq API.

## Running

```
cp .env.example .env   # then fill in GROQ_API_KEY
uv run health-agents ask         # main entrypoint: guardrail -> classifier -> routed agent
uv run health-agents summarize --file path/to/report.pdf
uv run health-agents summarize   # paste text, Ctrl-D to finish
uv run health-agents synthesize  # interactive interview, writes reports/health_report_*.pdf
uv run health-agents qna         # chat loop, type 'exit' to quit
uv run pytest
```
