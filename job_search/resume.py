"""Extract plain text from a resume file."""

from pathlib import Path

SUPPORTED_SUFFIXES = (".pdf", ".docx", ".txt", ".md")


def read_resume_text(path: str | Path) -> str:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Resume not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _read_pdf(path)
    elif suffix == ".docx":
        text = _read_docx(path)
    elif suffix in (".txt", ".md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported resume format {suffix!r}; use one of {', '.join(SUPPORTED_SUFFIXES)}")

    text = text.strip()
    if not text:
        raise ValueError(
            f"No text could be extracted from {path.name}. "
            "If it is a scanned/image PDF, export it as a text PDF or .docx first."
        )
    return text


def _read_pdf(path: Path) -> str:
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _read_docx(path: Path) -> str:
    import docx

    document = docx.Document(path)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)
