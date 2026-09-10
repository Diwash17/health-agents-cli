from pathlib import Path

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".txt", ".pdf"}


def load_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        return _read_pdf(path)
    raise ValueError(
        f"Unsupported file type: {suffix!r}. Supported types: {sorted(SUPPORTED_SUFFIXES)}"
    )


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()
