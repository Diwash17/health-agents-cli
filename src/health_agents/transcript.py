def format_transcript(qa_history: list[dict[str, str]]) -> str:
    blocks = [
        f"Q{i}: {qa['question']}\nA{i}: {qa['answer']}"
        for i, qa in enumerate(qa_history, start=1)
    ]
    return "\n\n".join(blocks)
