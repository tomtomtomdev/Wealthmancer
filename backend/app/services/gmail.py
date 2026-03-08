"""
Gmail IMAP service for searching and downloading financial statement PDFs.
"""

import email
import imaplib
import logging
import os
import re
import uuid
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

from app.config import UPLOAD_DIR

logger = logging.getLogger(__name__)

DEFAULT_KEYWORDS = [
    "statement",
    "billing",
    "tagihan",
    "rekening",
    "sekuritas",
    "portfolio",
    "soa",
    "e-statement",
    "mutasi",
]

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
IMAP_TIMEOUT = 30


def _decode_header_value(raw: str | None) -> str:
    """Decode an email header value that may be MIME-encoded."""
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded_parts: list[str] = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return "".join(decoded_parts)


def _build_search_criteria(
    keywords: list[str],
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """
    Build an IMAP SEARCH query string.

    Combines keyword OR-searches in the SUBJECT with optional date range.
    IMAP doesn't support OR across many terms neatly, so we search for each
    keyword separately and merge results.
    """
    criteria_parts: list[str] = []

    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            imap_date = dt.strftime("%d-%b-%Y")
            criteria_parts.append(f'SINCE {imap_date}')
        except ValueError:
            logger.warning("Invalid date_from format: %s", date_from)

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d")
            imap_date = dt.strftime("%d-%b-%Y")
            criteria_parts.append(f'BEFORE {imap_date}')
        except ValueError:
            logger.warning("Invalid date_to format: %s", date_to)

    return " ".join(criteria_parts)


def _sanitize_filename(filename: str) -> str:
    """Remove or replace characters that are unsafe for filenames."""
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    if not filename:
        filename = "attachment"
    return filename


def _connect_imap(email_addr: str, password: str) -> imaplib.IMAP4_SSL:
    """Create and authenticate an IMAP connection."""
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=IMAP_TIMEOUT)
    conn.login(email_addr, password)
    return conn


async def test_gmail_connection(email_addr: str, password: str) -> dict:
    """Test if Gmail credentials work. Returns {"success": bool, "message": str}."""
    try:
        conn = _connect_imap(email_addr, password)
        conn.select("INBOX", readonly=True)
        conn.logout()
        return {"success": True, "message": "Successfully connected to Gmail."}
    except imaplib.IMAP4.error as e:
        msg = str(e)
        if "AUTHENTICATIONFAILED" in msg.upper() or "Invalid credentials" in msg:
            return {
                "success": False,
                "message": "Authentication failed. Check your email and app password.",
            }
        return {"success": False, "message": f"IMAP error: {msg}"}
    except TimeoutError:
        return {"success": False, "message": "Connection timed out. Check your network."}
    except OSError as e:
        return {"success": False, "message": f"Connection error: {e}"}


async def search_gmail_for_statements(
    email_addr: str,
    password: str,
    search_keywords: list[str] | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    max_results: int = 50,
) -> list[dict]:
    """
    Search Gmail for financial statement PDFs.

    Default search keywords: ["statement", "billing", "tagihan", "rekening",
    "sekuritas", "portfolio", "soa", "e-statement", "mutasi"]

    Returns list of:
    {
        "message_id": str,
        "subject": str,
        "from": str,
        "date": str,
        "attachments": [{"filename": str, "size": int, "saved_path": str}]
    }
    """
    keywords = search_keywords or DEFAULT_KEYWORDS
    results: list[dict] = []
    seen_msg_ids: set[str] = set()

    try:
        conn = _connect_imap(email_addr, password)
    except imaplib.IMAP4.error as e:
        logger.error("Gmail IMAP auth failed: %s", e)
        raise ValueError(f"Authentication failed: {e}") from e
    except (TimeoutError, OSError) as e:
        logger.error("Gmail IMAP connection failed: %s", e)
        raise ConnectionError(f"Connection failed: {e}") from e

    try:
        conn.select("INBOX", readonly=True)
        date_criteria = _build_search_criteria(keywords, date_from, date_to)

        # Search for each keyword in SUBJECT separately and merge results
        all_msg_nums: list[bytes] = []
        for keyword in keywords:
            search_query = f'(SUBJECT "{keyword}"'
            if date_criteria:
                search_query += f" {date_criteria}"
            search_query += ")"

            try:
                status, data = conn.search(None, search_query)
                if status == "OK" and data[0]:
                    all_msg_nums.extend(data[0].split())
            except imaplib.IMAP4.error as e:
                logger.warning("Search failed for keyword '%s': %s", keyword, e)
                continue

        # Also search BODY for keywords (some emails have keywords in body only)
        for keyword in keywords:
            search_query = f'(BODY "{keyword}"'
            if date_criteria:
                search_query += f" {date_criteria}"
            search_query += ")"

            try:
                status, data = conn.search(None, search_query)
                if status == "OK" and data[0]:
                    all_msg_nums.extend(data[0].split())
            except imaplib.IMAP4.error as e:
                logger.warning("Body search failed for keyword '%s': %s", keyword, e)
                continue

        # Deduplicate message numbers
        unique_msg_nums = list(dict.fromkeys(all_msg_nums))

        # Limit results
        if len(unique_msg_nums) > max_results:
            unique_msg_nums = unique_msg_nums[-max_results:]  # Take most recent

        for msg_num in unique_msg_nums:
            try:
                result_entry = _process_message(conn, msg_num, seen_msg_ids)
                if result_entry and result_entry["attachments"]:
                    results.append(result_entry)
            except Exception as e:
                logger.warning("Error processing message %s: %s", msg_num, e)
                continue

    except Exception as e:
        logger.error("Error during Gmail search: %s", e)
        raise
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    return results


def _process_message(
    conn: imaplib.IMAP4_SSL,
    msg_num: bytes,
    seen_msg_ids: set[str],
) -> dict | None:
    """Fetch and process a single email message. Returns result dict or None."""
    status, msg_data = conn.fetch(msg_num, "(RFC822)")
    if status != "OK" or not msg_data or not msg_data[0]:
        return None

    raw_email = msg_data[0]
    if isinstance(raw_email, tuple):
        raw_email = raw_email[1]
    if not isinstance(raw_email, bytes):
        return None

    msg = email.message_from_bytes(raw_email)

    # Get message ID for dedup
    message_id = msg.get("Message-ID", str(uuid.uuid4()))
    if message_id in seen_msg_ids:
        return None
    seen_msg_ids.add(message_id)

    subject = _decode_header_value(msg.get("Subject"))
    sender = _decode_header_value(msg.get("From"))

    # Parse date
    date_str = ""
    try:
        date_header = msg.get("Date")
        if date_header:
            dt = parsedate_to_datetime(date_header)
            date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        date_str = msg.get("Date", "")

    # Find PDF attachments
    attachments: list[dict] = []
    for part in msg.walk():
        content_disposition = part.get("Content-Disposition")
        if content_disposition is None:
            continue

        if "attachment" not in content_disposition.lower():
            continue

        raw_filename = part.get_filename()
        filename = _decode_header_value(raw_filename) if raw_filename else None
        if not filename:
            continue

        if not filename.lower().endswith(".pdf"):
            continue

        # Download and save PDF
        payload = part.get_payload(decode=True)
        if not payload:
            continue

        safe_name = _sanitize_filename(filename)
        unique_name = f"{uuid.uuid4()}_{safe_name}"
        saved_path = os.path.join(UPLOAD_DIR, unique_name)

        try:
            with open(saved_path, "wb") as f:
                f.write(payload)

            attachments.append({
                "filename": filename,
                "size": len(payload),
                "saved_path": saved_path,
            })
        except OSError as e:
            logger.warning("Failed to save attachment %s: %s", filename, e)
            continue

    if not attachments:
        return None

    return {
        "message_id": message_id,
        "subject": subject,
        "from": sender,
        "date": date_str,
        "attachments": attachments,
    }
