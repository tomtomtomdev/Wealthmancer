"""
BNI Sekuritas consolidated account statement extractor.

Expected pdfplumber format:
- "Mr/Mrs. TOMMY YOHANES (23AA40752) User ID : 23AA40752"
- "SID : IDD0705LBQ91836"
- "Period : JANUARY 2026"
- "Total Asset : 1,326,737"
- Cash: "Reguler (Acc.ID : 10010186701, RDI : 1823773955) 104,737.41 104,737.41 104,737.41"
- Portfolio: "1 ADMF 100 13,700.00 8,300 1,370,000 830,000 0 (540,000)"
  Next line: "  Adira Dinamika Multi Finance 0"
- Parentheses around amounts mean negative values
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
    """Parse amount in English format. Parentheses = negative."""
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
    """Extract data from BNI Sekuritas consolidated account statement."""
    if not pages_text:
        return None

    full_text = "\n".join(pages_text)
    data: dict = {
        "user_id": None,
        "name": None,
        "sid": None,
        "period": None,
        "ae_name": None,
        "total_asset": None,
        "cash_summary": [],
        "cash_balance": None,
        "portfolio": [],
        "transactions": [],
    }
    confidence = 0.0

    # Name and User ID: "Mr/Mrs. TOMMY YOHANES (23AA40752) User ID : 23AA40752"
    name_match = re.search(r"Mr/Mrs\.\s+(.+?)\s+\((\w+)\)", full_text)
    if name_match:
        data["name"] = name_match.group(1).strip()
        data["user_id"] = name_match.group(2).strip()
        confidence += 0.2
    else:
        user_match = re.search(r"(?:User\s+ID|Client\s+(?:ID|Code))\s*[:\-]?\s*(\S+)", full_text, re.IGNORECASE)
        if user_match:
            data["user_id"] = user_match.group(1).strip()
            confidence += 0.1

    # SID: "SID : IDD0705LBQ91836"
    sid_match = re.search(r"SID\s*[:\-]?\s*(ID[\w\d]+)", full_text, re.IGNORECASE)
    if sid_match:
        data["sid"] = sid_match.group(1).strip()
        confidence += 0.1

    # Period: "Period : JANUARY 2026"
    period_match = re.search(
        r"(?:Period|Periode)\s*[:\-]?\s*(.+?)(?:\n|$)",
        full_text,
        re.IGNORECASE,
    )
    if period_match:
        data["period"] = period_match.group(1).strip()
        confidence += 0.05

    # A/E Name
    ae_match = re.search(r"A/?E\s+(?:Name)?\s*[:\-]?\s*(.+?)(?:\n|$)", full_text, re.IGNORECASE)
    if ae_match:
        data["ae_name"] = ae_match.group(1).strip()

    # Total Asset: "Total Asset : 1,326,737"
    asset_match = re.search(r"(?:Total\s+Asset|Total\s+Aset)\s*[:\-]?\s*(?:Rp\.?\s*)?([\d,]+\.?\d*)", full_text, re.IGNORECASE)
    if asset_match:
        data["total_asset"] = _parse_amount(asset_match.group(1))
        confidence += 0.1

    # Parse period dates from "JANUARY 2026" style
    period_start = None
    period_end = None
    if period_match:
        period_text = period_match.group(1).strip()
        # Try "MONTH YEAR" format
        m = re.match(r"(\w+)\s+(\d{4})", period_text, re.IGNORECASE)
        if m:
            month = _MONTH_MAP.get(m.group(1).lower())
            year = int(m.group(2))
            if month:
                period_start = date(year, month, 1).isoformat()
                # Last day of month
                if month == 12:
                    period_end = date(year, 12, 31).isoformat()
                else:
                    period_end = (date(year, month + 1, 1).replace(day=1) - __import__("datetime").timedelta(days=1)).isoformat()
        else:
            # Try date range patterns
            date_ranges = re.findall(r"(\d{1,2}[/\-\s]\w+[/\-\s]\d{2,4})", period_text)
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

    # Parse sections
    section = None
    for page_text in pages_text:
        lines = page_text.split("\n")
        for line in lines:
            line_stripped = line.strip()
            upper = line_stripped.upper()

            # Detect sections
            if "CASH SUMMARY" in upper or "RINGKASAN KAS" in upper or "SALDO KAS" in upper:
                section = "cash"
                continue
            elif "PORTFOLIO STATEMENT" in upper or "PORTFOLIO" in upper or "PORTOFOLIO" in upper:
                section = "portfolio"
                continue
            elif "TRANSACTION" in upper or "TRANSAKSI" in upper:
                section = "transactions"
                continue

            if not line_stripped:
                continue

            # Stop at section boundaries
            if re.match(r"^Total\b", line_stripped, re.IGNORECASE) and section in ("portfolio", "cash"):
                section = None
                continue
            if re.match(r"(?:DISCLAIMER|Note|Catatan)", line_stripped, re.IGNORECASE):
                section = None
                continue

            if section == "cash":
                # Parse cash line: "Reguler (Acc.ID : 10010186701, RDI : 1823773955) 104,737.41 104,737.41 104,737.41"
                cash_match = re.search(
                    r"(.*?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
                    line_stripped,
                )
                if cash_match:
                    cash_entry = {
                        "account_id": cash_match.group(1).strip(),
                        "current_month": _parse_amount(cash_match.group(2)),
                        "previous_month": _parse_amount(cash_match.group(3)),
                        "balance": _parse_amount(cash_match.group(4)),
                    }
                    data["cash_summary"].append(cash_entry)
                    # Set cash_balance to first cash entry balance
                    if data["cash_balance"] is None:
                        data["cash_balance"] = cash_entry["balance"]
                # Skip header lines
                elif re.match(r"(?:No|Name|Cur)", line_stripped, re.IGNORECASE) and (
                    "Balance" in line_stripped or "Month" in line_stripped
                ):
                    continue

            elif section == "portfolio":
                # Skip headers
                if re.match(r"(?:No|Name|Stock)\s+", line_stripped, re.IGNORECASE) and (
                    "Volume" in line_stripped or "Avg" in line_stripped or "Price" in line_stripped
                    or "Available" in line_stripped or "Blocked" in line_stripped
                ):
                    continue
                # Skip sub-header lines
                if "Blocked Volume" in line_stripped or "Blocked" in line_stripped:
                    continue

                # Parse portfolio line:
                # "1 ADMF 100 13,700.00 8,300 1,370,000 830,000 0 (540,000)"
                portfolio_match = re.match(
                    r"(\d+)\s+([A-Z]{3,5})\s+(\d+)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+(\(?[\d,]+\.?\d*\)?)",
                    line_stripped,
                )
                if portfolio_match:
                    holding = {
                        "stock_id": portfolio_match.group(2),
                        "available_volume": int(portfolio_match.group(3)),
                        "avg_price": _parse_amount(portfolio_match.group(4)),
                        "closing_price": _parse_amount(portfolio_match.group(5)),
                        "sec_value": _parse_amount(portfolio_match.group(6)),
                        "market_value": _parse_amount(portfolio_match.group(7)),
                        "collateral_value": _parse_amount(portfolio_match.group(8)),
                        "unrealized_pnl": _parse_amount(portfolio_match.group(9)),
                    }
                    data["portfolio"].append(holding)
                    continue

                # Stock name continuation line (e.g., "  Adira Dinamika Multi Finance 0")
                # Skip these - they're just additional info

            elif section == "transactions":
                # Parse transaction: date description debit credit balance
                txn_match = re.match(
                    r"(\d{1,2}[/\-]\d{1,2}[/\-]?\d{0,4})\s+(.+?)\s+([\d,]+\.?\d*)\s*([\d,]+\.?\d*)?\s*([\d,]+\.?\d*)?",
                    line_stripped,
                )
                if txn_match:
                    txn = {
                        "date": txn_match.group(1),
                        "description": txn_match.group(2).strip(),
                        "amount": _parse_amount(txn_match.group(3)),
                        "credit": _parse_amount(txn_match.group(4)) if txn_match.group(4) else None,
                        "balance": _parse_amount(txn_match.group(5)) if txn_match.group(5) else None,
                    }
                    data["transactions"].append(txn)

    if data["portfolio"]:
        confidence += 0.2
    if data["cash_summary"]:
        confidence += 0.1
    if data["transactions"]:
        confidence += 0.1

    confidence = min(confidence, 1.0)

    return {
        "data": data,
        "confidence_score": confidence,
        "document_type": "securities_consolidated",
        "period_start": period_start,
        "period_end": period_end,
    }
