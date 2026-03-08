"""
CIMB Niaga credit card statement extractor.

Expected format from pdfplumber:
- First line: card holder name (e.g., "TOMMY YOHANES")
- Card number masked: 5481 17XX XXXX 8086
- Statement date: "Tgl. Statement 17/02/26" (DD/MM/YY)
- Due date: "Tgl. Jatuh Tempo 05/03/26" (DD/MM/YY)
- Credit limit in table after "Batas Kredit"
- Transactions with DD/MM DD/MM description amount [CR]
- ENDING BALANCE for current balance
"""

import re
from datetime import date

import logging

logger = logging.getLogger(__name__)

# Indonesian month name mapping
_MONTH_MAP: dict[str, int] = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "agustus": 8,
    "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "okt": 10, "oct": 10, "nov": 11, "des": 12, "dec": 12,
}


def _parse_indonesian_date(text: str, default_year: int | None = None) -> date | None:
    """Parse dates in Indonesian format like '15 Januari 2024', '15/01/2024', or '15/01/24'."""
    text = text.strip()

    # Try DD/MM/YYYY
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    # Try DD/MM/YY
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})", text)
    if m:
        year = int(m.group(3)) + 2000
        return date(year, int(m.group(2)), int(m.group(1)))

    # Try DD Month YYYY
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", text, re.IGNORECASE)
    if m:
        month = _MONTH_MAP.get(m.group(2).lower())
        if month:
            return date(int(m.group(3)), month, int(m.group(1)))

    # Try DD/MM without year
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})$", text)
    if m and default_year:
        return date(default_year, int(m.group(2)), int(m.group(1)))

    return None


def _parse_amount(text: str) -> float:
    """Parse amount string in English format (commas as thousands, dots as decimal).

    Examples: '56,000.00' -> 56000.0, '1,186,841.83' -> 1186841.83
    """
    text = text.strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    # English format: commas are thousands separators, dots are decimal
    text = text.replace(",", "")
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return 0.0


def extract(pages_text: list[str]) -> dict | None:
    """Extract data from CIMB Niaga credit card statement pages."""
    if not pages_text:
        return None

    full_text = "\n".join(pages_text)
    first_page = pages_text[0]
    data: dict = {
        "card_holder": None,
        "card_number": None,
        "card_type": None,
        "statement_date": None,
        "due_date": None,
        "credit_limit": None,
        "current_balance": None,
        "minimum_payment": None,
        "transactions": [],
    }
    confidence = 0.0

    # Extract card holder name - first non-empty line, or text before "Jenis Kartu"
    name_match = re.search(r"^([A-Z][A-Z\s]+?)(?:\s+Jenis Kartu|\n)", first_page, re.MULTILINE)
    if name_match:
        data["card_holder"] = name_match.group(1).strip()
        confidence += 0.1
    else:
        # Fallback: try "Nama" pattern
        name_match = re.search(r"(?:Nama|Name)\s*[:\-]?\s*(.+)", first_page, re.IGNORECASE)
        if name_match:
            data["card_holder"] = name_match.group(1).strip()
            confidence += 0.1
        else:
            # Try first non-empty line
            for line in first_page.split("\n"):
                line = line.strip()
                if line and re.match(r"^[A-Z][A-Z\s]+$", line):
                    data["card_holder"] = line
                    confidence += 0.1
                    break

    # Extract card number (masked)
    card_match = re.search(r"(\d{4}\s+\d{2}XX\s+XXXX\s+\d{4})", full_text)
    if not card_match:
        card_match = re.search(r"(\d{4}[\s\-*X]+[\dX*]{2,4}[\s\-*X]+[\dX*]{4}[\s\-*X]+\d{4})", full_text)
    if not card_match:
        card_match = re.search(r"([\dX*]{4}[\s\-]?[\dX*]{4}[\s\-]?[\dX*]{4}[\s\-]?[\dX*]{4})", full_text)
    if card_match:
        data["card_number"] = card_match.group(1).strip()
        confidence += 0.1

    # Card type
    for card_type in ["VISA", "MASTERCARD", "MASTER CARD", "MC GOLD", "PLATINUM", "GOLD", "CLASSIC"]:
        if card_type.lower() in full_text.lower():
            data["card_type"] = card_type
            confidence += 0.05
            break

    # Statement date: "Tgl. Statement 17/02/26" (DD/MM/YY format)
    stmt_match = re.search(
        r"Tgl\.?\s*Statement\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        full_text,
        re.IGNORECASE,
    )
    if not stmt_match:
        stmt_match = re.search(
            r"(?:Tanggal\s+(?:Cetak|Statement)|Statement\s+Date)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
            full_text,
            re.IGNORECASE,
        )
    if not stmt_match:
        stmt_match = re.search(
            r"(?:Tanggal\s+(?:Cetak|Statement)|Statement\s+Date)\s*[:\-]?\s*(\d{1,2}[/\-\s]\w+[/\-\s]\d{2,4})",
            full_text,
            re.IGNORECASE,
        )
    if stmt_match:
        parsed = _parse_indonesian_date(stmt_match.group(1))
        if parsed:
            data["statement_date"] = parsed.isoformat()
            confidence += 0.1

    # Due date: "Tgl. Jatuh Tempo 05/03/26" (DD/MM/YY format)
    due_match = re.search(
        r"Tgl\.?\s*Jatuh\s+Tempo\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        full_text,
        re.IGNORECASE,
    )
    if not due_match:
        due_match = re.search(
            r"(?:Tanggal\s+Jatuh\s+Tempo|Due\s+Date)\s*[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
            full_text,
            re.IGNORECASE,
        )
    if not due_match:
        due_match = re.search(
            r"(?:Tanggal\s+Jatuh\s+Tempo|Due\s+Date)\s*[:\-]?\s*(\d{1,2}[/\-\s]\w+[/\-\s]\d{2,4})",
            full_text,
            re.IGNORECASE,
        )
    if due_match:
        parsed = _parse_indonesian_date(due_match.group(1))
        if parsed:
            data["due_date"] = parsed.isoformat()
            confidence += 0.05

    # Credit limit - look for "Batas Kredit" followed by amount on same or next line
    # Format: "Batas Kredit Batas Penarikan Tunai ..."
    # Next line: "MC GOLD REGULER 28,000,000.00 4,200,000.00 ..."
    limit_match = re.search(
        r"Batas\s+Kredit.*?\n.*?(?:MC|VISA|MASTER).*?\s+([\d,]+\.\d{2})",
        full_text,
        re.IGNORECASE,
    )
    if not limit_match:
        limit_match = re.search(
            r"(?:Batas\s+Kredit|Credit\s+Limit)\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,]+\.\d{2})",
            full_text,
            re.IGNORECASE,
        )
    if limit_match:
        data["credit_limit"] = _parse_amount(limit_match.group(1))
        confidence += 0.05

    # Current balance - try ENDING BALANCE first, then Tagihan Baru/Total Tagihan
    balance_match = re.search(
        r"ENDING\s+BALANCE\s+([\d,]+\.\d{2})",
        full_text,
        re.IGNORECASE,
    )
    if not balance_match:
        balance_match = re.search(
            r"(?:Total\s+(?:Tagihan|Baru)|(?:New|Current)\s+Balance|Tagihan\s+Baru)\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,]+\.\d{2})",
            full_text,
            re.IGNORECASE,
        )
    if balance_match:
        data["current_balance"] = _parse_amount(balance_match.group(1))
        confidence += 0.1

    # Minimum payment - from the header table row with card number
    # Format: "5481 17XX XXXX 8086 4,247,403.83 0.00 212,371.00"
    # The minimum payment is the third amount in that row
    min_match = re.search(
        r"\d{4}\s+\d{2}XX\s+XXXX\s+\d{4}\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
        full_text,
    )
    if min_match:
        data["minimum_payment"] = _parse_amount(min_match.group(3))
        confidence += 0.05
    else:
        # Fallback
        min_match2 = re.search(
            r"(?:Pembayaran\s+Minimum|Minimum\s+Payment|Tagihan\s+Minimum)\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,]+\.\d{2})",
            full_text,
            re.IGNORECASE,
        )
        if min_match2:
            data["minimum_payment"] = _parse_amount(min_match2.group(1))
            confidence += 0.05

    # Determine statement year for date parsing
    stmt_year = None
    if data.get("statement_date"):
        stmt_year = int(data["statement_date"][:4])

    # Extract transactions
    # Look for card-specific sections with transaction lines
    # Format: "20/01 22/01 SHOPEE Jakarta IDN 56,000.00"
    #         "25/01 25/01 PAYMENT-THANK YOU 1,187,000.00 CR"
    in_transactions = False
    for page_text in pages_text:
        lines = page_text.split("\n")
        for line in lines:
            line_stripped = line.strip()

            # Detect start of transaction detail section
            if re.search(r"LAST\s+BALANCE", line_stripped, re.IGNORECASE):
                in_transactions = True
                # Parse LAST BALANCE line itself
                lb_match = re.search(r"LAST\s+BALANCE\s+([\d,]+\.\d{2})", line_stripped, re.IGNORECASE)
                if lb_match:
                    txn = {
                        "date": None,
                        "posting_date": None,
                        "description": "LAST BALANCE",
                        "amount": _parse_amount(lb_match.group(1)),
                        "type": "info",
                    }
                    data["transactions"].append(txn)
                continue

            if "PERINCIAN TAGIHAN" in line_stripped.upper() or "RINCIAN TRANSAKSI" in line_stripped.upper():
                in_transactions = True
                continue

            if not in_transactions:
                continue

            # Skip empty lines
            if not line_stripped:
                continue

            # Stop at ENDING BALANCE or new card section
            if re.match(r"ENDING\s+BALANCE", line_stripped, re.IGNORECASE):
                eb_match = re.search(r"ENDING\s+BALANCE\s+([\d,]+\.\d{2})", line_stripped, re.IGNORECASE)
                if eb_match:
                    txn = {
                        "date": None,
                        "posting_date": None,
                        "description": "ENDING BALANCE",
                        "amount": _parse_amount(eb_match.group(1)),
                        "type": "info",
                    }
                    data["transactions"].append(txn)
                in_transactions = False
                continue

            # Skip headers
            if re.match(r"(?:Tgl|Tanggal)", line_stripped) and ("Keterangan" in line_stripped or "Jumlah" in line_stripped):
                continue

            # Parse transaction line: DD/MM DD/MM description amount [CR]
            txn_match = re.match(
                r"(\d{1,2}/\d{1,2})\s+(\d{1,2}/\d{1,2})\s+(.*?)\s+([\d,]+\.\d{2})\s*(CR)?\s*$",
                line_stripped,
                re.IGNORECASE,
            )
            if txn_match:
                txn_date_str = txn_match.group(1)
                posting_date_str = txn_match.group(2)
                description = txn_match.group(3).strip()
                amount = _parse_amount(txn_match.group(4))
                is_credit = txn_match.group(5) is not None

                txn_date = _parse_indonesian_date(txn_date_str, default_year=stmt_year)
                posting_date = _parse_indonesian_date(posting_date_str, default_year=stmt_year)

                txn = {
                    "date": txn_date.isoformat() if txn_date else txn_date_str,
                    "posting_date": posting_date.isoformat() if posting_date else posting_date_str,
                    "description": description,
                    "amount": amount,
                    "type": "credit" if is_credit else "debit",
                }
                data["transactions"].append(txn)
                continue

            # Try single-date format
            txn_match2 = re.match(
                r"(\d{1,2}/\d{1,2})\s+(.*?)\s+([\d,]+\.\d{2})\s*(CR)?\s*$",
                line_stripped,
                re.IGNORECASE,
            )
            if txn_match2:
                txn_date_str = txn_match2.group(1)
                description = txn_match2.group(2).strip()
                amount = _parse_amount(txn_match2.group(3))
                is_credit = txn_match2.group(4) is not None

                txn_date = _parse_indonesian_date(txn_date_str, default_year=stmt_year)

                txn = {
                    "date": txn_date.isoformat() if txn_date else txn_date_str,
                    "posting_date": None,
                    "description": description,
                    "amount": amount,
                    "type": "credit" if is_credit else "debit",
                }
                data["transactions"].append(txn)

    if data["transactions"]:
        confidence += 0.3

    # Ensure confidence is capped
    confidence = min(confidence, 1.0)

    # Determine period
    period_start = None
    period_end = None
    if data.get("statement_date"):
        period_end = data["statement_date"]
    if data["transactions"]:
        dates = [t["date"] for t in data["transactions"] if isinstance(t["date"], str) and len(t["date"]) == 10]
        if dates:
            period_start = min(dates)
            if not period_end:
                period_end = max(dates)

    return {
        "data": data,
        "confidence_score": confidence,
        "document_type": "credit_card_statement",
        "period_start": period_start,
        "period_end": period_end,
    }
