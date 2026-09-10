from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from health_agents.prompts.synthesis import SECTION_HEADERS

REPORT_TITLE = "Health Report"


def write_report_pdf(report_text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"health_report_{timestamp}.pdf"

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, REPORT_TITLE, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0,
        8,
        f"Generated {datetime.now():%Y-%m-%d %H:%M}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    for raw_line in report_text.splitlines():
        line = raw_line.strip()
        if not line:
            pdf.ln(3)
        elif line in SECTION_HEADERS:
            pdf.set_font("Helvetica", "B", 13)
            pdf.ln(2)
            pdf.multi_cell(0, 8, line, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 12)
        else:
            pdf.set_font("Helvetica", "", 12)
            pdf.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(path))
    return path
