import re

import pdfplumber


def extract_text_from_pdf(file_path: str) -> list[str]:
    """Extract text from each page of a PDF file using pdfplumber."""
    pages_text: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages_text.append(text)
    return pages_text


# Institution detection patterns - order matters, more specific patterns first
_INSTITUTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("CIMB Niaga", re.compile(r"CIMB\s*Niaga|PT\s+Bank\s+CIMB\s+Niaga", re.IGNORECASE)),
    ("BCA Sekuritas", re.compile(r"BCA\s+Sekuritas|PT\s+BCA\s+Sekuritas", re.IGNORECASE)),
    ("Mandiri Sekuritas", re.compile(r"Mandiri\s+Sekuritas|PT\s+Mandiri\s+Sekuritas", re.IGNORECASE)),
    ("BNI Sekuritas", re.compile(r"BNI\s+Sekuritas|PT\s+BNI\s+Sekuritas", re.IGNORECASE)),
    ("Stockbit", re.compile(r"Stockbit|PT\s+Stockbit\s+Sekuritas", re.IGNORECASE)),
    ("BCA", re.compile(r"(?:PT\s+)?Bank\s+Central\s+Asia|BCA|Rekening\s+Tahapan", re.IGNORECASE)),
]


def detect_institution(text: str) -> str | None:
    """Detect the financial institution from extracted text content."""
    for name, pattern in _INSTITUTION_PATTERNS:
        if pattern.search(text):
            return name
    return None
