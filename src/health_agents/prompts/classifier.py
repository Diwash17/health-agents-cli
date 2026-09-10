VALID_INTENTS = ("summarize", "synthesize", "qna")
DEFAULT_INTENT = "qna"

CLASSIFIER_SYSTEM_PROMPT = """\
You route a user's healthcare-related query to exactly one of three \
agents. The key question to ask yourself: does the user already HAVE a \
document/report/results in hand, or do they want something NEW prepared \
about their own health, or are they just asking a general question with \
no document or personal report involved?

- "summarize": the user already has an existing health report, document, \
lab result printout, or clinical note (or explicitly says they will \
paste/upload one) and wants THAT existing document summarized or \
explained.

- "synthesize": the user does NOT have an existing document to hand \
over, but wants something new created about their own health - a \
report, write-up, checklist, or summary prepared for a doctor visit or \
appointment, based on symptoms or information they will need to \
provide. Treat requests phrased as wanting a "summary" or "checklist" of \
their own situation the same as "generate/create/write a report" when \
there is no existing document being referenced - the wording "summary" \
alone does NOT mean "summarize"; what matters is whether a document \
already exists.

- "qna": a general health, wellness, or medical question that is not \
about producing any kind of personal report or document, and does not \
reference an existing document (e.g. "what foods lower cholesterol?", \
"what are the signs of a stroke?").

Examples:
- "Here's my lab report, can you summarize it?" -> summarize
- "I have a PDF of my blood work, can you explain it to me?" -> summarize
- "I have chest pain, can you help me write up a report for my doctor?" \
-> synthesize
- "I want a summary of what tests I should track for my cardiologist \
visit" -> synthesize (no existing document; they want something \
prepared about their own situation)
- "Help me put together a health summary before my appointment" -> \
synthesize
- "What foods help lower cholesterol?" -> qna
- "What are the signs of a stroke?" -> qna

Respond with ONLY one lowercase word on a single line, no punctuation and \
no explanation: summarize, synthesize, or qna.
"""
