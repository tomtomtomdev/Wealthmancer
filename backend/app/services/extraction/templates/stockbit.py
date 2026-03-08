"""
Stockbit statement of account extractor.

Expected pdfplumber format:
- "Client 0088552 TOMMY YOHANES"
- "Email tommy.yohanes@gmail.com"
- "Phone 6281285965506"
- "SID IDD0705UU759746"
- "Cash Investor 70,600.99"
- Portfolio: "BFIN BFI Finance 300 1,103.75 705 331,125 211,500 -119,625 -36.13"
  with possible multi-line stock names (continuation on next line)
- "T O T A L" line for totals
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


def _parse_date(text: str) -> date | None:
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
    text = re.sub(r"[^\d.]", "", text)
    try:
        val = float(text)
        return -val if negative else val
    except ValueError:
        return 0.0


def extract(pages_text: list[str]) -> dict | None:
    """Extract data from Stockbit statement of account."""
    if not pages_text:
        return None

    full_text = "\n".join(pages_text)
    data: dict = {
        "client_id": None,
        "name": None,
        "address": None,
        "email": None,
        "phone": None,
        "sid": None,
        "bank": None,
        "currency": "IDR",
        "cash_investor": None,
        "cash": None,
        "portfolio_value": None,
        "equity_nab": None,
        "avail_limit": None,
        "portfolio": [],
        "transactions": [],
    }
    confidence = 0.0

    # Client ID and Name: "Client 0088552 TOMMY YOHANES Cash 70,601"
    # The name is between the client number and "Cash" keyword
    client_match = re.search(r"Client\s+(\d+)\s+([A-Z][A-Z\s]+?)\s+(?:Cash|$)", full_text)
    if client_match:
        data["client_id"] = client_match.group(1).strip()
        data["name"] = client_match.group(2).strip()
        confidence += 0.2
    else:
        # Fallback
        client_match2 = re.search(r"Client\s+(\d+)\s+([A-Z][A-Z\s]+?)(?:\n|$)", full_text)
        if client_match2:
            data["client_id"] = client_match2.group(1).strip()
            data["name"] = client_match2.group(2).strip()
            confidence += 0.15

    # Address
    addr_match = re.search(r"(?:Address|Alamat)\s*[:\-]?\s*(.+?)(?:\n|$)", full_text, re.IGNORECASE)
    if addr_match:
        data["address"] = addr_match.group(1).strip()

    # Email: "Email tommy.yohanes@gmail.com"
    email_match = re.search(r"[Ee]mail\s*[:\-]?\s*([\w.+-]+@[\w-]+\.[\w.]+)", full_text)
    if email_match:
        data["email"] = email_match.group(1).strip()
        confidence += 0.05

    # Phone: "Phone 6281285965506"
    phone_match = re.search(r"(?:Phone|Telepon|HP|Telp|Mobile)\s*[:\-]?\s*([\d\-+\s()]+\d)", full_text, re.IGNORECASE)
    if phone_match:
        data["phone"] = phone_match.group(1).strip()
        confidence += 0.05

    # SID: "BCA 4996784347 / IDR IDD0705UU759746" or "SID IDD0705UU759746" or "SID\nIDD0705UU759746"
    sid_match = re.search(r"(IDD\w+)", full_text)
    if sid_match:
        data["sid"] = sid_match.group(1).strip()
        confidence += 0.1

    # Bank
    bank_match = re.search(r"(?:Bank\s+(?:Name|Nama)?)\s*[:\-]?\s*(.+?)(?:\n|$)", full_text, re.IGNORECASE)
    if bank_match:
        data["bank"] = bank_match.group(1).strip()

    # Financial summary values
    for field, patterns in [
        ("cash_investor", [r"Cash\s+Investor\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,.]+)"]),
        ("cash", [r"(?:^|\n)\s*Cash\s+([\d,.]+)"]),
        ("portfolio_value", [r"Portfolio\s+([\d,.]+)"]),
        ("equity_nab", [r"Equity\s+(?:NAB|NAV)\s+([\d,.]+)"]),
        ("avail_limit", [r"Avail(?:able)?\s+Limit\s+([\d,.]+)"]),
    ]:
        for pattern in patterns:
            m = re.search(pattern, full_text, re.IGNORECASE)
            if m:
                data[field] = _parse_amount(m.group(1))
                confidence += 0.05
                break

    # Period
    period_match = re.search(
        r"(?:Period|Periode|Statement\s+Date)\s*[:\-]?\s*(.+?)(?:\n|$)",
        full_text,
        re.IGNORECASE,
    )
    period_start = None
    period_end = None
    if period_match:
        period_text = period_match.group(1).strip()
        date_ranges = re.findall(r"(\d{1,2}[/\-]\w+[/\-]\d{2,4})", period_text)
        if len(date_ranges) >= 2:
            d1, d2 = _parse_date(date_ranges[0]), _parse_date(date_ranges[1])
            if d1:
                period_start = d1.isoformat()
            if d2:
                period_end = d2.isoformat()
        elif len(date_ranges) == 1:
            d1 = _parse_date(date_ranges[0])
            if d1:
                period_end = d1.isoformat()

    # Parse portfolio
    # Format: "BFIN BFI Finance 300 1,103.75 705 331,125 211,500 -119,625 -36.13"
    # Some lines have "Special Notes" or "Margin" columns that may be empty
    # Multi-line: continuation of stock name on next line (e.g., "Indonesia Tbk.")
    section = None
    for page_text in pages_text:
        lines = page_text.split("\n")
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            upper = line_stripped.upper()

            if "PORTFOLIO STATEMENT" in upper or ("PORTFOLIO" in upper and "TRANSACTION" not in upper):
                section = "portfolio"
                continue
            elif "TRANSACTION" in upper or "STATEMENT OF ACCOUNT" in upper:
                section = "transactions"
                continue

            if not line_stripped:
                continue

            # Stop at TOTAL line (with or without spaces)
            if re.match(r"T\s*O\s*T\s*A\s*L", line_stripped) or re.match(r"^TOTAL\b", line_stripped, re.IGNORECASE):
                if section == "portfolio":
                    section = None
                continue

            if re.match(r"(?:DISCLAIMER|Note|Catatan|Page\s+\d)", line_stripped, re.IGNORECASE):
                continue

            if section == "portfolio":
                # Skip headers
                if re.match(r"(?:Stocks?|Ticker|No\.?)\s+", line_stripped, re.IGNORECASE) and (
                    "Qty" in line_stripped or "Quantity" in line_stripped or "Price" in line_stripped
                    or "Margin" in line_stripped or "Close" in line_stripped
                ):
                    continue
                # Skip sub-header lines like "(Rp.) %"
                if re.match(r"^\(Rp\.?\)", line_stripped):
                    continue

                # Try to match portfolio line starting with ticker
                # "BFIN BFI Finance 300 1,103.75 705 331,125 211,500 -119,625 -36.13"
                portfolio_match = re.match(
                    r"([A-Z]{3,5})\s+(.+?)\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)\s+(-?[\d,.]+)",
                    line_stripped,
                )
                if portfolio_match:
                    holding = {
                        "stock_ticker": portfolio_match.group(1),
                        "stock_name": portfolio_match.group(2).strip(),
                        "quantity": int(portfolio_match.group(3)),
                        "buying_price": _parse_amount(portfolio_match.group(4)),
                        "close_price": _parse_amount(portfolio_match.group(5)),
                        "buying_value": _parse_amount(portfolio_match.group(6)),
                        "market_value": _parse_amount(portfolio_match.group(7)),
                        "unrealized_gain_loss_rp": _parse_amount(portfolio_match.group(8)),
                        "unrealized_gain_loss_pct": _parse_amount(portfolio_match.group(9)),
                    }
                    data["portfolio"].append(holding)
                    continue

                # Try shorter match (fewer columns)
                portfolio_match2 = re.match(
                    r"([A-Z]{3,5})\s+(.+?)\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)",
                    line_stripped,
                )
                if portfolio_match2:
                    holding = {
                        "stock_ticker": portfolio_match2.group(1),
                        "stock_name": portfolio_match2.group(2).strip(),
                        "quantity": int(portfolio_match2.group(3)),
                        "buying_price": _parse_amount(portfolio_match2.group(4)),
                        "close_price": _parse_amount(portfolio_match2.group(5)),
                        "buying_value": _parse_amount(portfolio_match2.group(6)),
                        "market_value": _parse_amount(portfolio_match2.group(7)),
                        "unrealized_gain_loss_rp": None,
                        "unrealized_gain_loss_pct": None,
                    }
                    data["portfolio"].append(holding)
                    continue

                # Continuation line for stock name - skip (name already captured)

            elif section == "transactions":
                # Parse transaction line
                txn_match = re.match(
                    r"(\d{1,2}[/\-]\d{1,2}[/\-]?\d{0,4})\s+(.+?)\s+([\d,.]+)\s*([DC]?[BR]?)\s*$",
                    line_stripped,
                )
                if not txn_match:
                    txn_match = re.match(
                        r"(\d{1,2}[/\-]\d{1,2}[/\-]?\d{0,4})\s+(.+?)\s+([\d,.]+)",
                        line_stripped,
                    )
                if txn_match:
                    txn = {
                        "date": txn_match.group(1),
                        "description": txn_match.group(2).strip(),
                        "amount": _parse_amount(txn_match.group(3)),
                        "type": "credit" if txn_match.lastindex and txn_match.lastindex >= 4 and txn_match.group(4) and "C" in txn_match.group(4) else "debit",
                    }
                    data["transactions"].append(txn)

    if data["portfolio"]:
        confidence += 0.2
    if data["transactions"]:
        confidence += 0.1

    confidence = min(confidence, 1.0)

    return {
        "data": data,
        "confidence_score": confidence,
        "document_type": "securities_statement",
        "period_start": period_start,
        "period_end": period_end,
    }
