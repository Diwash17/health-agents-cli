from health_agents.transcript import format_transcript


def test_format_transcript_numbers_pairs() -> None:
    qa_history = [
        {"question": "How are you feeling?", "answer": "Tired."},
        {"question": "Since when?", "answer": "Three days."},
    ]

    result = format_transcript(qa_history)

    assert result == (
        "Q1: How are you feeling?\nA1: Tired.\n\n"
        "Q2: Since when?\nA2: Three days."
    )


def test_format_transcript_empty() -> None:
    assert format_transcript([]) == ""
