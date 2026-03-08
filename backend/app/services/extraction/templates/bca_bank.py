"""
BCA bank statement (Rekening Tahapan) extractor.

Expected pdfplumber format:
- "TOMMY YOHANES NO. REKENING : 0160135654"
- "PERIODE : APRIL 2025"
- "TANGGAL KETERANGAN CBG MUTASI SALDO"
- "01/04 SALDO AWAL 8,966,158.15"
- "01/04 TRSF E-BANKING DB 0104/FTFVA/WS95031 128,500.00 DB 8,837,658.15"
- Multi-line transactions: continuation lines start with spaces and no date
- Amounts in English format (commas as thousands, dots as decimal)
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
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8,
    "october": 10, "december": 12,
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

    m = re.match(r"(\d{1,2})[/\-](\d{1,2})$", text)
    if m and default_year:
        return date(default_year, int(m.group(2)), int(m.group(1)))
    return None


def _parse_amount(text: str) -> float:
    """Parse amount in English format (commas as thousands, dots as decimal)."""
    text = text.strip()
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1]
    if text.startswith("-"):
        negative = True
        text = text[1:]
    text = text.replace(",", "")
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return 0.0


def extract(pages_text: list[str]) -> dict | None:
    """Extract data from BCA bank statement (Rekening Tahapan)."""
    if not pages_text:
        return None

    full_text = "\n".join(pages_text)
    first_page = pages_text[0]
    data: dict = {
        "account_holder": None,
        "account_number": None,
        "period": None,
        "currency": "IDR",
        "opening_balance": None,
        "closing_balance": None,
        "transactions": [],
    }
    confidence = 0.0

    # Account holder and number: "TOMMY YOHANES NO. REKENING : 0160135654"
    name_acct_match = re.search(
        r"^([A-Z][A-Z\s]+?)\s+NO\.?\s*REKENING\s*:\s*(\d+)",
        first_page,
        re.MULTILINE | re.IGNORECASE,
    )
    if name_acct_match:
        data["account_holder"] = name_acct_match.group(1).strip()
        data["account_number"] = name_acct_match.group(2).strip()
        confidence += 0.2
    else:
        # Fallback: account holder
        name_match = re.search(
            r"(?:Nama|Name|Atas\s+Nama)\s*[:\-]?\s*(.+?)(?:\n|$)",
            first_page,
            re.IGNORECASE,
        )
        if name_match:
            data["account_holder"] = name_match.group(1).strip()
            confidence += 0.1

        # Fallback: account number
        acct_match = re.search(
            r"(?:No\.?\s*(?:Rekening|Account)|Nomor\s+Rekening)\s*[:\-]?\s*(\d[\d\s\-]+\d)",
            full_text,
            re.IGNORECASE,
        )
        if acct_match:
            data["account_number"] = acct_match.group(1).strip().replace(" ", "")
            confidence += 0.1

    # Period: "PERIODE : APRIL 2025"
    period_match = re.search(
        r"PERIODE\s*:\s*(\w+\s+\d{4})",
        full_text,
        re.IGNORECASE,
    )
    if period_match:
        data["period"] = period_match.group(1).strip()
        confidence += 0.05
    else:
        period_match = re.search(
            r"(?:Period|Periode)\s*[:\-]?\s*(.+?)(?:\n|$)",
            full_text,
            re.IGNORECASE,
        )
        if period_match:
            data["period"] = period_match.group(1).strip()
            confidence += 0.05

    # Parse period dates and statement year
    period_start = None
    period_end = None
    stmt_year = None
    if data.get("period"):
        period_text = data["period"]
        # Try "MONTH YEAR" format like "APRIL 2025"
        m = re.match(r"(\w+)\s+(\d{4})", period_text, re.IGNORECASE)
        if m:
            month = _MONTH_MAP.get(m.group(1).lower())
            year = int(m.group(2))
            if month:
                stmt_year = year
                period_start = date(year, month, 1).isoformat()
                if month == 12:
                    period_end = date(year, 12, 31).isoformat()
                else:
                    period_end = (date(year, month + 1, 1).replace(day=1) - __import__("datetime").timedelta(days=1)).isoformat()
        else:
            date_ranges = re.findall(r"(\d{1,2}[/\-\s]\w+[/\-\s]\d{2,4})", period_text)
            if len(date_ranges) >= 2:
                d1, d2 = _parse_date(date_ranges[0]), _parse_date(date_ranges[1])
                if d1:
                    period_start = d1.isoformat()
                    stmt_year = d1.year
                if d2:
                    period_end = d2.isoformat()
                    stmt_year = d2.year
            elif len(date_ranges) == 1:
                d1 = _parse_date(date_ranges[0])
                if d1:
                    period_end = d1.isoformat()
                    stmt_year = d1.year

    # Try to extract year from full text if not from period
    if not stmt_year:
        year_match = re.search(r"20\d{2}", full_text)
        if year_match:
            stmt_year = int(year_match.group())

    # Currency
    if "USD" in full_text:
        data["currency"] = "USD"
    elif "EUR" in full_text:
        data["currency"] = "EUR"

    # Opening balance: "SALDO AWAL 8,966,158.15"
    saldo_match = re.search(
        r"SALDO\s+AWAL\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,]+\.\d{2})",
        full_text,
        re.IGNORECASE,
    )
    if saldo_match:
        data["opening_balance"] = _parse_amount(saldo_match.group(1))
        confidence += 0.1

    # Extract transactions
    in_transactions = False
    current_description_parts: list[str] = []
    current_txn: dict | None = None

    for page_text in pages_text:
        lines = page_text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            upper = line_stripped.upper()

            # Detect start of transaction table
            if "TANGGAL" in upper and ("KETERANGAN" in upper or "MUTASI" in upper):
                in_transactions = True
                continue

            if "SALDO AWAL" in upper:
                in_transactions = True
                continue

            if not in_transactions:
                continue

            # Skip empty lines - but don't skip continuation lines
            if not line_stripped:
                continue

            # Skip repeated headers
            if "TANGGAL" in upper and "KETERANGAN" in upper:
                continue

            # Closing balance
            if "SALDO AKHIR" in upper:
                closing_match = re.search(r"([\d,]+\.\d{2})\s*$", line_stripped)
                if closing_match:
                    data["closing_balance"] = _parse_amount(closing_match.group(1))
                in_transactions = False
                # Save last transaction
                if current_txn:
                    if current_description_parts:
                        current_txn["description"] = " ".join(current_description_parts)
                    data["transactions"].append(current_txn)
                    current_txn = None
                continue

            # Try to parse a transaction line
            # Format: DD/MM description [CBG] amount DB|CR balance
            # "01/04 TRSF E-BANKING DB 0104/FTFVA/WS95031 128,500.00 DB 8,837,658.15"
            # Or credit: "01/04 BI-FAST CR BIF TRANSFER DR 2,002,500.00 10,840,158.15"
            txn_match = re.match(
                r"(\d{1,2}/\d{1,2})\s+(.+?)\s+([\d,]+\.\d{2})\s+(DB)\s+([\d,]+\.\d{2})",
                line_stripped,
                re.IGNORECASE,
            )
            if txn_match:
                # Debit transaction (has DB suffix)
                if current_txn:
                    if current_description_parts:
                        current_txn["description"] = " ".join(current_description_parts)
                    data["transactions"].append(current_txn)

                txn_date = _parse_date(txn_match.group(1), default_year=stmt_year)
                description = txn_match.group(2).strip()

                current_txn = {
                    "date": txn_date.isoformat() if txn_date else txn_match.group(1),
                    "description": description,
                    "cbg": None,
                    "amount": _parse_amount(txn_match.group(3)),
                    "type": "debit",
                    "balance": _parse_amount(txn_match.group(5)),
                }
                current_description_parts = [description]
                continue

            # Credit transaction (no DB/CR suffix on amount, or CR)
            txn_match2 = re.match(
                r"(\d{1,2}/\d{1,2})\s+(.+?)\s+([\d,]+\.\d{2})\s+(CR)\s+([\d,]+\.\d{2})",
                line_stripped,
                re.IGNORECASE,
            )
            if txn_match2:
                if current_txn:
                    if current_description_parts:
                        current_txn["description"] = " ".join(current_description_parts)
                    data["transactions"].append(current_txn)

                txn_date = _parse_date(txn_match2.group(1), default_year=stmt_year)
                description = txn_match2.group(2).strip()

                current_txn = {
                    "date": txn_date.isoformat() if txn_date else txn_match2.group(1),
                    "description": description,
                    "cbg": None,
                    "amount": _parse_amount(txn_match2.group(3)),
                    "type": "credit",
                    "balance": _parse_amount(txn_match2.group(5)),
                }
                current_description_parts = [description]
                continue

            # Credit without explicit CR (just amount then balance)
            txn_match3 = re.match(
                r"(\d{1,2}/\d{1,2})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$",
                line_stripped,
                re.IGNORECASE,
            )
            if txn_match3:
                if current_txn:
                    if current_description_parts:
                        current_txn["description"] = " ".join(current_description_parts)
                    data["transactions"].append(current_txn)

                txn_date = _parse_date(txn_match3.group(1), default_year=stmt_year)
                description = txn_match3.group(2).strip()

                current_txn = {
                    "date": txn_date.isoformat() if txn_date else txn_match3.group(1),
                    "description": description,
                    "cbg": None,
                    "amount": _parse_amount(txn_match3.group(3)),
                    "type": "credit",
                    "balance": _parse_amount(txn_match3.group(4)),
                }
                current_description_parts = [description]
                continue

            # SALDO AWAL line (opening balance as a "transaction")
            if "SALDO AWAL" in upper:
                saldo_match2 = re.match(
                    r"(\d{1,2}/\d{1,2})\s+SALDO\s+AWAL\s+([\d,]+\.\d{2})",
                    line_stripped,
                    re.IGNORECASE,
                )
                if saldo_match2:
                    if current_txn:
                        if current_description_parts:
                            current_txn["description"] = " ".join(current_description_parts)
                        data["transactions"].append(current_txn)

                    txn_date = _parse_date(saldo_match2.group(1), default_year=stmt_year)
                    current_txn = {
                        "date": txn_date.isoformat() if txn_date else saldo_match2.group(1),
                        "description": "SALDO AWAL",
                        "cbg": None,
                        "amount": _parse_amount(saldo_match2.group(2)),
                        "type": "info",
                        "balance": _parse_amount(saldo_match2.group(2)),
                    }
                    current_description_parts = ["SALDO AWAL"]
                    if data["opening_balance"] is None:
                        data["opening_balance"] = current_txn["amount"]
                        confidence += 0.1
                continue

            # Continuation line (no date at start) - part of multi-line transaction
            if current_txn and not re.match(r"^\d{1,2}/\d{1,2}", line_stripped):
                # Skip separator lines like "-"
                if line_stripped != "-":
                    current_description_parts.append(line_stripped)

    # Don't forget the last transaction
    if current_txn:
        if current_description_parts:
            current_txn["description"] = " ".join(current_description_parts)
        data["transactions"].append(current_txn)

    if data["transactions"]:
        confidence += 0.3

    # Extract period from transactions if not found
    if not period_start and data["transactions"]:
        dates = [t["date"] for t in data["transactions"] if isinstance(t["date"], str) and len(t["date"]) == 10]
        if dates:
            period_start = min(dates)
            if not period_end:
                period_end = max(dates)

    confidence = min(confidence, 1.0)

    return {
        "data": data,
        "confidence_score": confidence,
        "document_type": "bank_statement",
        "period_start": period_start,
        "period_end": period_end,
    }
