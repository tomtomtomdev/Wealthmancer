"""
Mandiri Sekuritas client statement extractor.

Expected pdfplumber format:
- "Client ID M359B21C TOMMY YOHANES"
- "KSEI No CC0018IP900187"
- "SID No IDD0705LBQ91836"
- "Email tommy.yohanes@gmail.com MTBI Account 1040005863985"
- "Date From Thursday, 01-Jan-26 To : Saturday, 31-Jan-26"
- Transaction table: No. TrxDate DueDate Description Price Volume Amount Debet Credit Balance Penalty
- CLIENT PORTFOLIO table: No. StockID AvgPrice ClosePrice Volume StockValue MarketValue LiquidityValue Unrealized
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

    # Try DD-Mon-YY like "01-Jan-26"
    m = re.match(r"(\d{1,2})[/\-](\w{3,})[/\-](\d{2,4})", text)
    if m:
        month = _MONTH_MAP.get(m.group(2).lower())
        if month:
            year = int(m.group(3))
            if year < 100:
                year += 2000
            return date(year, month, int(m.group(1)))

    # Try DD/MM/YYYY or DD-MM-YYYY
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})", text)
    if m:
        year = int(m.group(3))
        if year < 100:
            year += 2000
        return date(year, int(m.group(2)), int(m.group(1)))

    # Try DD Month YYYY
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
    """Extract data from Mandiri Sekuritas client statement."""
    if not pages_text:
        return None

    full_text = "\n".join(pages_text)
    data: dict = {
        "client_id": None,
        "name": None,
        "ksei": None,
        "sid": None,
        "email": None,
        "phone": None,
        "mtbi_account": None,
        "period": None,
        "cash_balance": None,
        "portfolio": [],
    }
    confidence = 0.0

    # Client ID and Name: "Client ID M359B21C TOMMY YOHANES C.P. Office..."
    client_name_match = re.search(
        r"Client\s+ID\s+(\S+)\s+([A-Z][A-Z\s]+?)(?:\s+C\.P\.\s|\s+Office\s|\n|$)",
        full_text,
    )
    if client_name_match:
        data["client_id"] = client_name_match.group(1).strip()
        data["name"] = client_name_match.group(2).strip()
        confidence += 0.2
    else:
        # Fallback
        client_match = re.search(r"(?:Client\s+(?:ID|Code))\s*[:\-]?\s*([A-Z\d]+)", full_text, re.IGNORECASE)
        if client_match:
            data["client_id"] = client_match.group(1).strip()
            confidence += 0.1
        name_match = re.search(r"(?:Client\s+Name|Nama)\s*[:\-]?\s*(.+?)(?:\n|$)", full_text, re.IGNORECASE)
        if name_match:
            data["name"] = name_match.group(1).strip()
            confidence += 0.1

    # KSEI: "KSEI No CC0018IP900187"
    ksei_match = re.search(r"KSEI\s*(?:No\.?|Number)?\s*[:\-]?\s*(\S+)", full_text, re.IGNORECASE)
    if ksei_match:
        data["ksei"] = ksei_match.group(1).strip()
        confidence += 0.1

    # SID: "SID No IDD0705LBQ91836"
    sid_match = re.search(r"SID\s*(?:No\.?)?\s*[:\-]?\s*(ID[\w\d]+)", full_text, re.IGNORECASE)
    if sid_match:
        data["sid"] = sid_match.group(1).strip()
        confidence += 0.1

    # Email
    email_match = re.search(r"[Ee]mail\s*[:\-]?\s*([\w.+-]+@[\w-]+\.[\w.]+)", full_text)
    if email_match:
        data["email"] = email_match.group(1).strip()
        confidence += 0.05

    # Phone
    phone_match = re.search(r"(?:Phone|Telepon|HP|Telp|Mobile)\s*[:\-]?\s*([\d\-+\s()]+\d)", full_text, re.IGNORECASE)
    if phone_match:
        data["phone"] = phone_match.group(1).strip()
        confidence += 0.05

    # MTBI Account: "MTBI Account 1040005863985"
    mtbi_match = re.search(r"MTBI\s*(?:Account|Acc)?\s*[:\-]?\s*(\d+)", full_text, re.IGNORECASE)
    if mtbi_match:
        data["mtbi_account"] = mtbi_match.group(1).strip()

    # Period: "Date From Thursday, 01-Jan-26 To : Saturday, 31-Jan-26"
    period_match = re.search(
        r"Date\s+From\s+\w+,?\s*(\d{1,2}-\w{3}-\d{2,4})\s+To\s*:?\s*\w+,?\s*(\d{1,2}-\w{3}-\d{2,4})",
        full_text,
        re.IGNORECASE,
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
        confidence += 0.05
    else:
        # Fallback period patterns
        period_match2 = re.search(
            r"(?:Period|Periode)\s*[:\-]?\s*(.+?)(?:\n|$)",
            full_text,
            re.IGNORECASE,
        )
        if period_match2:
            data["period"] = period_match2.group(1).strip()
            confidence += 0.05
            date_ranges = re.findall(r"(\d{1,2}[/\-]\w{3,}[/\-]\d{2,4})", period_match2.group(1))
            if len(date_ranges) >= 2:
                d1, d2 = _parse_date(date_ranges[0]), _parse_date(date_ranges[1])
                if d1:
                    period_start = d1.isoformat()
                if d2:
                    period_end = d2.isoformat()

    # Cash balance - look for "BEGINNING BALANCE" or ending balance in transaction table
    cash_match = re.search(
        r"(?:Cash\s+Balance|Saldo\s+Kas)\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,]+\.?\d*)",
        full_text,
        re.IGNORECASE,
    )
    if cash_match:
        data["cash_balance"] = _parse_amount(cash_match.group(1))
        confidence += 0.1

    # Extract portfolio from CLIENT PORTFOLIO section
    # Format: "1 ADMF 13,700 8,300 100 1,370,000 830,000 0 -540,000"
    in_portfolio = False
    for page_text in pages_text:
        lines = page_text.split("\n")
        for line in lines:
            line_stripped = line.strip()

            if "CLIENT PORTFOLIO" in line_stripped.upper() or "PORTOFOLIO" in line_stripped.upper():
                in_portfolio = True
                continue

            if not in_portfolio or not line_stripped:
                continue

            # Skip header lines
            if re.match(r"(?:No\.?|Stock)\s+", line_stripped, re.IGNORECASE) and (
                "Volume" in line_stripped or "Avg" in line_stripped or "Price" in line_stripped or "StockID" in line_stripped
            ):
                continue

            # Stop at totals or new sections
            if re.match(r"(?:TOTAL|Grand\s+Total|Note|Catatan)", line_stripped, re.IGNORECASE):
                in_portfolio = False
                continue

            # Parse portfolio line with regex:
            # No StockID AvgPrice ClosePrice Volume StockValue MarketValue LiquidityValue Unrealized
            # "1 ADMF 13,700 8,300 100 1,370,000 830,000 0 -540,000"
            portfolio_match = re.match(
                r"(\d+)\s+([A-Z]{3,5})\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(-?[\d,]+\.?\d*)",
                line_stripped,
            )
            if portfolio_match:
                holding = {
                    "stock_id": portfolio_match.group(2),
                    "avg_price": _parse_amount(portfolio_match.group(3)),
                    "close_price": _parse_amount(portfolio_match.group(4)),
                    "volume": int(_parse_amount(portfolio_match.group(5))),
                    "stock_value": _parse_amount(portfolio_match.group(6)),
                    "market_value": _parse_amount(portfolio_match.group(7)),
                    "liquidity_value": _parse_amount(portfolio_match.group(8)),
                    "unrealized_pnl": _parse_amount(portfolio_match.group(9)),
                }
                data["portfolio"].append(holding)
                continue

            # Fallback: try splitting by whitespace
            parts = re.split(r"\s+", line_stripped)
            if len(parts) >= 6 and parts[0].isdigit() and re.match(r"^[A-Z]{3,5}$", parts[1]):
                try:
                    holding = {
                        "stock_id": parts[1],
                        "avg_price": _parse_amount(parts[2]) if len(parts) > 2 else None,
                        "close_price": _parse_amount(parts[3]) if len(parts) > 3 else None,
                        "volume": int(_parse_amount(parts[4])) if len(parts) > 4 else 0,
                        "stock_value": _parse_amount(parts[5]) if len(parts) > 5 else None,
                        "market_value": _parse_amount(parts[6]) if len(parts) > 6 else None,
                        "liquidity_value": _parse_amount(parts[7]) if len(parts) > 7 else None,
                        "unrealized_pnl": _parse_amount(parts[8]) if len(parts) > 8 else None,
                    }
                    data["portfolio"].append(holding)
                except (ValueError, IndexError):
                    pass

    if data["portfolio"]:
        confidence += 0.2

    confidence = min(confidence, 1.0)

    return {
        "data": data,
        "confidence_score": confidence,
        "document_type": "securities_portfolio",
        "period_start": period_start,
        "period_end": period_end,
    }
