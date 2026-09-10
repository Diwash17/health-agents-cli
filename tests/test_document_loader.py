from pathlib import Path

import pytest

from health_agents.io.document_loader import load_document


def test_load_txt_file(tmp_path: Path) -> None:
    report = tmp_path / "report.txt"
    report.write_text("Patient presented with mild fever.", encoding="utf-8")

    assert load_document(report) == "Patient presented with mild fever."


def test_load_document_rejects_unsupported_extension(tmp_path: Path) -> None:
    other = tmp_path / "report.docx"
    other.write_text("irrelevant", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_document(other)
