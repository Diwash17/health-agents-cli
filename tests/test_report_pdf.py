from pathlib import Path

from pypdf import PdfReader

from health_agents.io.report_pdf import write_report_pdf


def test_write_report_pdf_creates_readable_pdf(tmp_path: Path) -> None:
    report_text = (
        "Chief Complaint\n"
        "Patient reports a three-day headache.\n\n"
        "Recommendations\n"
        "Rest and hydration advised."
    )

    path = write_report_pdf(report_text, tmp_path)

    assert path.exists()
    assert path.parent == tmp_path

    extracted = PdfReader(str(path)).pages[0].extract_text()
    assert "Chief Complaint" in extracted
    assert "three-day headache" in extracted
    assert "Rest and hydration advised" in extracted
