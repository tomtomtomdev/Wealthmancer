"""
BCA Sekuritas statement of account extractor.

Expected pdfplumber format:
- "01/01/2026 Upto 31/01/2026"
- "24NP TOMMY YOHANES"
- "SID IDD0705UU759746"
- "Bank BCA 4959393190"
- Transaction table with comma-as-decimal format: "0,00"
- NOTE: BCA Sekuritas uses COMMA as decimal separator (Indonesian/European style)
"""

import re
from datetime import date

import logging

logger = logging.getLogger(__name__)

_MONTH_MAP: dict[str, int] = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "okt": 10, "oct": 10, "nov": 11, "des": 12, "dec": 12,
}


def _parse_date(text: str, default_year: int | None = None) -> date | None:
    text = text.strip()
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", text)
    if m:
        year = int(m.group(3))
        if year < 100:
            year += 2000
        return date(year, int(m.group(2)), int(m.group(1)))

    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
    if m:
        month = _MONTH_MAP.get(m.group(2).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(1)))

    m = re.match(r"(\d{1,2})[/\-](\d{1,2})", text)
    if m and default_year:
        return date(default_year, int(m.group(2)), int(m.group(1)))
    return None


def _parse_amount(text: str) -> float:
    """Parse amount in INDONESIAN format (dots as thousands, commas as decimal).

    BCA Sekuritas uses comma as decimal separator: "0,00", "1.234,56"
    This is the ONLY template that keeps the original Indonesian format parsing.
    """
    text = text.strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    # Indonesian format: dots are thousands, commas are decimal
    text = text.replace(".", "").replace(",", ".")
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return 0.0


def extract(pages_text: list[str]) -> dict | None:
    """Extract data from BCA Sekuritas statement of account."""
    if not pages_text:
        return None

    full_text = "\n".join(pages_text)
    first_page = pages_text[0]
    data: dict = {
        "account_holder": None,
        "client_id": None,
        "sid": None,
        "bank_account": None,
        "email": None,
        "phone": None,
        "period": None,
        "currency": "IDR",
        "transactions": [],
    }
    confidence = 0.0

    # Period: "01/01/2026 Upto 31/01/2026"
    period_match = re.search(
        r"(\d{1,2}/\d{1,2}/\d{4})\s+[Uu]pto\s+(\d{1,2}/\d{1,2}/\d{4})",
        full_text,
    )
    period_start = None
    period_end = None
    if period_match:
        d1 = _parse_date(period_match.group(1))
        d2 = _parse_date(period_match.group(2))
        if d1:
            period_start = d1.isoformat()
        if d2:
            period_end = d2.isoformat()
        data["period"] = f"{period_match.group(1)} - {period_match.group(2)}"
        confidence += 0.1
    else:
        # Fallback period
        period_match2 = re.search(
            r"(?:Period|Periode)\s*[:\-]?\s*(\d{1,2}[/\-\s]\w+[/\-\s]\d{2,4})\s*(?:s/?d|to|\-)\s*(\d{1,2}[/\-\s]\w+[/\-\s]\d{2,4})",
            full_text,
            re.IGNORECASE,
        )
        if period_match2:
            data["period"] = f"{period_match2.group(1).strip()} - {period_match2.group(2).strip()}"
            d1 = _parse_date(period_match2.group(1))
            d2 = _parse_date(period_match2.group(2))
            if d1:
                period_start = d1.isoformat()
            if d2:
                period_end = d2.isoformat()
            confidence += 0.1

    # Client ID and Name: "24NP TOMMY YOHANES"
    # Look for a line with a short alphanumeric code followed by an all-caps name
    client_name_match = re.search(
        r"^(\d{2}[A-Z]{2})\s+([A-Z][A-Z\s]+?)(?:\n|$)",
        full_text,
        re.MULTILINE,
    )
    if client_name_match:
        data["client_id"] = client_name_match.group(1).strip()
        data["account_holder"] = client_name_match.group(2).strip()
        confidence += 0.2
    else:
        # Fallback
        client_match = re.search(r"(?:Client\s+(?:ID|Code)|Kode\s+Nasabah)\s*[:\-]?\s*(\S+)", full_text, re.IGNORECASE)
        if client_match:
            data["client_id"] = client_match.group(1).strip()
            confidence += 0.1
        name_match = re.search(r"(?:Client\s+Name|Nama\s+(?:Nasabah|Client))\s*[:\-]?\s*(.+)", full_text, re.IGNORECASE)
        if name_match:
            data["account_holder"] = name_match.group(1).strip()
            confidence += 0.1

    # SID: "SID IDD0705UU759746"
    sid_match = re.search(r"SID\s*[:\-]?\s*(ID[\w\d]+)", full_text, re.IGNORECASE)
    if sid_match:
        data["sid"] = sid_match.group(1).strip()
        confidence += 0.1

    # Bank account: "Bank BCA 4959393190"
    bank_match = re.search(r"Bank\s+(\w+)\s+(\d{5,})", full_text, re.IGNORECASE)
    if bank_match:
        data["bank_account"] = f"{bank_match.group(1)} {bank_match.group(2)}"
        confidence += 0.05
    else:
        bank_match2 = re.search(r"(?:Bank\s+Account|Rekening\s+Bank|No\.?\s*Rek)\s*[:\-]?\s*(\d[\d\s\-]+\d)", full_text, re.IGNORECASE)
        if bank_match2:
            data["bank_account"] = bank_match2.group(1).strip()
            confidence += 0.05

    # Email
    email_match = re.search(r"[Ee]mail\s*[:\-]?\s*([\w.+-]+@[\w-]+\.[\w.]+)", full_text)
    if email_match:
        data["email"] = email_match.group(1).strip()
        confidence += 0.05

    # Phone
    phone_match = re.search(r"(?:Phone|Telepon|HP|Telp)\s*[:\-]?\s*([\d\-+\s()]+\d)", full_text, re.IGNORECASE)
    if phone_match:
        data["phone"] = phone_match.group(1).strip()
        confidence += 0.05

    # Extract transactions from STATEMENT OF ACCOUNT section
    in_transactions = False
    for page_text in pages_text:
        lines = page_text.split("\n")
        for line in lines:
            line_stripped = line.strip()

            if re.search(r"STATEMENT\s+OF\s+ACCOUNT", line_stripped, re.IGNORECASE):
                in_transactions = True
                continue

            if re.search(r"(?:Transaction|Transaksi)\s*(?:Detail|List)", line_stripped, re.IGNORECASE):
                in_transactions = True
                continue

            if not in_transactions or not line_stripped:
                continue

            # Skip header lines
            if re.match(r"(?:ate|Date|Tanggal|No\.?)\s+", line_stripped, re.IGNORECASE) and (
                "Ref" in line_stripped or "Description" in line_stripped or "Due" in line_stripped
            ):
                continue

            # Stop at TOTAL line
            if re.match(r"T\s*O\s*T\s*A\s*L", line_stripped) or re.match(r"^TOTAL\b", line_stripped, re.IGNORECASE):
                in_transactions = False
                continue

            # Parse transaction lines
            # Format may have truncated dates from PDF: "/26 01/01/26 Balance 0,00 0,00 0,00 0,00"
            # Or full: "01/01/26 01/01/26 Balance 0,00 0,00 0,00 0,00"
            txn_match = re.match(
                r"/?(\d{1,2})?/?(\d{2})?\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)",
                line_stripped,
            )
            if txn_match:
                txn = {
                    "date": txn_match.group(3) if txn_match.group(3) else line_stripped[:8],
                    "due_date": txn_match.group(3),
                    "description": txn_match.group(4).strip() if txn_match.group(4) else None,
                    "debit": _parse_amount(txn_match.group(5)) if txn_match.group(5) else None,
                    "credit": _parse_amount(txn_match.group(6)) if txn_match.group(6) else None,
                    "ending_balance": _parse_amount(txn_match.group(7)) if txn_match.group(7) else None,
                    "penalty": _parse_amount(txn_match.group(8)) if txn_match.group(8) else None,
                }
                data["transactions"].append(txn)
                continue

            # Simpler pattern
            txn_match2 = re.match(
                r"(\d{1,2}/\d{1,2}/?\d{0,4})\s+(.+?)\s+([\d.,]+)\s+([\d.,]+)",
                line_stripped,
            )
            if txn_match2:
                txn = {
                    "date": txn_match2.group(1),
                    "due_date": None,
                    "description": txn_match2.group(2).strip(),
                    "debit": _parse_amount(txn_match2.group(3)),
                    "credit": _parse_amount(txn_match2.group(4)),
                    "ending_balance": None,
                    "penalty": None,
                }
                data["transactions"].append(txn)

    if data["transactions"]:
        confidence += 0.3

    confidence = min(confidence, 1.0)

    return {
        "data": data,
        "confidence_score": confidence,
        "document_type": "securities_statement",
        "period_start": period_start,
        "period_end": period_end,
    }
