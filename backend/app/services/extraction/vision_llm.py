import base64
import json
import logging
from pathlib import Path

from app.config import ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# Institution-specific prompt fragments
_INSTITUTION_PROMPTS: dict[str, str] = {
    "CIMB Niaga": (
        "This is a CIMB Niaga credit card statement. "
        "Extract: card_holder, card_number (masked), card_type, statement_date, due_date, "
        "credit_limit, current_balance, minimum_payment, and a list of transactions with "
        "date, posting_date, description, amount, type (debit or credit - lines ending with CR are credits)."
    ),
    "BCA Sekuritas": (
        "This is a BCA Sekuritas statement of account. "
        "Extract: account_holder, client_id, sid, bank_account, email, phone, period, currency, "
        "and a list of transactions with date, due_date, ref, description, debit, credit, ending_balance, penalty."
    ),
    "Mandiri Sekuritas": (
        "This is a Mandiri Sekuritas client statement. "
        "Extract: client_id, name, ksei, sid, email, phone, mtbi_account, period, cash_balance, "
        "and portfolio list with stock_id, volume, avg_price, close_price, stock_value, market_value, "
        "liquidity_value, unrealized_pnl."
    ),
    "BNI Sekuritas": (
        "This is a BNI Sekuritas consolidated account statement. "
        "Extract: user_id, sid, period, ae_name, total_asset, "
        "cash_summary with account_id, current_month, previous_month, balance, "
        "and portfolio with stock_name, available_volume, avg_price, closing_price, "
        "sec_value, market_value, collateral_value, unrealized_pnl, "
        "and transactions from the statement."
    ),
    "Stockbit": (
        "This is a Stockbit statement of account. "
        "Extract: client_id, name, address, email, phone, sid, bank, currency, "
        "cash_investor, cash, portfolio_value, equity_nab, avail_limit, "
        "and portfolio list with stock_ticker, stock_name, special_notes, margin, "
        "quantity, buying_price, close_price, buying_value, market_value, "
        "unrealized_gain_loss_rp, unrealized_gain_loss_pct, "
        "and transactions from the statement section."
    ),
    "BCA": (
        "This is a BCA bank statement (Rekening Tahapan). "
        "Extract: account_holder, account_number, period, currency, opening_balance, "
        "and a list of transactions with date, description, cbg, amount, type (DB or CR), balance."
    ),
}

_DEFAULT_PROMPT = (
    "This is an Indonesian financial document. "
    "Extract all relevant financial data including account holder info, "
    "account numbers, balances, transactions, and portfolio holdings. "
    "Return structured JSON."
)


async def extract_with_vision(
    file_path: str,
    institution: str | None = None,
) -> dict | None:
    """
    Extract financial data from a PDF using Claude's vision capabilities.
    Converts PDF pages to images and sends them to the Anthropic API.

    Returns parsed JSON dict or None if API key is not configured.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not configured, skipping vision extraction")
        return None

    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.error("pdf2image not installed, skipping vision extraction")
        return None

    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed, skipping vision extraction")
        return None

    # Convert PDF pages to images
    try:
        images = convert_from_path(file_path, dpi=200, fmt="png")
    except Exception as e:
        logger.error("Failed to convert PDF to images: %s", e)
        return None

    # Encode images to base64
    image_contents: list[dict] = []
    for img in images[:10]:  # Limit to 10 pages to control cost
        import io

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        image_contents.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64,
                },
            }
        )

    # Build prompt
    inst_prompt = _INSTITUTION_PROMPTS.get(institution or "", _DEFAULT_PROMPT)
    system_prompt = (
        "You are a financial document parser specializing in Indonesian financial statements. "
        "Extract data accurately and return ONLY valid JSON. "
        "Use null for missing values. Amounts should be numbers without currency symbols or thousand separators."
    )

    user_content: list[dict] = list(image_contents)
    user_content.append(
        {
            "type": "text",
            "text": f"{inst_prompt}\n\nReturn the extracted data as a single JSON object.",
        }
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )

        response_text = response.content[0].text

        # Try to extract JSON from the response
        json_match = _extract_json(response_text)
        if json_match:
            return json.loads(json_match)

        # Try parsing the whole response as JSON
        return json.loads(response_text)

    except json.JSONDecodeError as e:
        logger.error("Failed to parse vision LLM response as JSON: %s", e)
        return {"raw_response": response_text, "parse_error": str(e)}
    except Exception as e:
        logger.error("Vision LLM extraction failed: %s", e)
        return None


def _extract_json(text: str) -> str | None:
    """Extract JSON from text that may contain markdown code blocks."""
    import re

    # Try ```json ... ``` blocks
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try finding JSON object boundaries
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None
