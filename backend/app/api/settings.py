"""
Settings API router.

Handles app configuration and Gmail IMAP integration.
"""

import hashlib
import json
import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.db.database import get_db
from app.models.models import Account, Document
from app.models.settings import AppSetting
from app.schemas.schemas import (
    DocumentUploadResponse,
    GmailImportRequest,
    GmailSearchRequest,
    GmailSearchResponse,
    GmailSearchResult,
    GmailTestRequest,
    GmailTestResponse,
    MultiUploadResponse,
    SettingResponse,
    SettingsUpdateRequest,
)
from app.services.gmail import search_gmail_for_statements, test_gmail_connection

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_setting(db: Session, key: str) -> str | None:
    """Get a setting value by key."""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    return setting.value if setting else None


def _mask_value(value: str | None) -> str:
    """Mask a sensitive value for display."""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


@router.get("/settings", response_model=list[SettingResponse])
async def get_settings(db: Session = Depends(get_db)):
    """Get all settings. Passwords are masked."""
    settings = db.query(AppSetting).all()
    result: list[SettingResponse] = []
    for s in settings:
        value = s.value
        is_encrypted = s.encrypted == "true"
        if is_encrypted and value:
            value = _mask_value(value)
        result.append(SettingResponse(key=s.key, value=value, encrypted=is_encrypted))
    return result


@router.post("/settings", response_model=list[SettingResponse])
async def save_settings(
    request: SettingsUpdateRequest,
    db: Session = Depends(get_db),
):
    """Save settings (key-value pairs)."""
    encrypted_keys = {"gmail_app_password"}
    result: list[SettingResponse] = []

    for key, value in request.settings.items():
        existing = db.query(AppSetting).filter(AppSetting.key == key).first()
        is_encrypted = key in encrypted_keys

        if existing:
            existing.value = value
            existing.encrypted = "true" if is_encrypted else "false"
        else:
            setting = AppSetting(
                key=key,
                value=value,
                encrypted="true" if is_encrypted else "false",
            )
            db.add(setting)

        display_value = _mask_value(value) if is_encrypted else value
        result.append(SettingResponse(key=key, value=display_value, encrypted=is_encrypted))

    db.commit()
    return result


@router.post("/settings/gmail/test", response_model=GmailTestResponse)
async def gmail_test(
    request: GmailTestRequest,
    db: Session = Depends(get_db),
):
    """Test Gmail IMAP connection."""
    email_addr = request.email or _get_setting(db, "gmail_email")
    password = request.password or _get_setting(db, "gmail_app_password")

    if not email_addr or not password:
        return GmailTestResponse(
            success=False,
            message="Email and app password are required. Save them in settings first.",
        )

    result = await test_gmail_connection(email_addr, password)
    return GmailTestResponse(**result)


@router.post("/settings/gmail/search", response_model=GmailSearchResponse)
async def gmail_search(
    request: GmailSearchRequest,
    db: Session = Depends(get_db),
):
    """Search Gmail for financial statement PDFs."""
    email_addr = request.email or _get_setting(db, "gmail_email")
    password = request.password or _get_setting(db, "gmail_app_password")

    if not email_addr or not password:
        raise HTTPException(
            status_code=400,
            detail="Email and app password are required. Save them in settings first.",
        )

    keywords = request.keywords
    if not keywords:
        saved_keywords = _get_setting(db, "gmail_search_keywords")
        if saved_keywords:
            keywords = [k.strip() for k in saved_keywords.split(",") if k.strip()]

    try:
        results = await search_gmail_for_statements(
            email_addr=email_addr,
            password=password,
            search_keywords=keywords,
            date_from=request.date_from,
            date_to=request.date_to,
            max_results=request.max_results,
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error("Gmail search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    total_pdfs = sum(len(r["attachments"]) for r in results)
    search_results = [
        GmailSearchResult(
            message_id=r["message_id"],
            subject=r["subject"],
            sender=r["from"],
            date=r["date"],
            attachments=r["attachments"],
        )
        for r in results
    ]

    return GmailSearchResponse(results=search_results, total_pdfs=total_pdfs)


@router.post("/settings/gmail/import", response_model=MultiUploadResponse)
async def gmail_import(
    request: GmailImportRequest,
    db: Session = Depends(get_db),
):
    """Import selected PDFs from Gmail search results (runs extraction pipeline)."""
    from app.api.upload import _parse_date_str, _store_extraction_results
    from app.services.extraction.pipeline import extract_document
    from app.services.matching import group_accounts_into_persons, match_accounts

    documents: list[DocumentUploadResponse] = []
    duplicates: list[dict] = []
    all_new_accounts: list[Account] = []

    for file_path in request.file_paths:
        if not os.path.exists(file_path):
            logger.warning("File not found: %s", file_path)
            continue

        if not file_path.lower().endswith(".pdf"):
            logger.warning("Skipping non-PDF file: %s", file_path)
            continue

        # Calculate file hash for dedup
        with open(file_path, "rb") as f:
            file_content = f.read()
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Check for duplicates
        existing_doc = (
            db.query(Document).filter(Document.file_hash == file_hash).first()
        )
        if existing_doc:
            original_filename = os.path.basename(file_path)
            duplicates.append({
                "filename": original_filename,
                "existing_document_id": existing_doc.id,
            })
            # Remove the downloaded file
            try:
                os.remove(file_path)
            except OSError:
                pass
            continue

        original_filename = os.path.basename(file_path)
        # Strip the UUID prefix if present (from gmail download)
        display_name = original_filename
        parts = original_filename.split("_", 1)
        if len(parts) > 1 and len(parts[0]) == 36:
            display_name = parts[1]

        # Run extraction pipeline
        try:
            extraction = await extract_document(file_path)
        except Exception as e:
            logger.error("Extraction failed for %s: %s", original_filename, e)
            extraction = {
                "institution": None,
                "document_type": None,
                "confidence_score": 0.0,
                "data": {},
                "period_start": None,
                "period_end": None,
            }

        # Create document record
        doc = Document(
            filename=display_name,
            file_hash=file_hash,
            institution=extraction.get("institution"),
            document_type=extraction.get("document_type"),
            period_start=_parse_date_str(extraction.get("period_start")),
            period_end=_parse_date_str(extraction.get("period_end")),
            raw_extracted=json.dumps(extraction.get("data", {})),
            confidence_score=extraction.get("confidence_score", 0.0),
        )
        db.add(doc)
        db.flush()

        # Store structured data
        try:
            new_accounts = _store_extraction_results(db, doc, extraction)
            all_new_accounts.extend(new_accounts)
        except Exception as e:
            logger.error("Failed to store results for %s: %s", original_filename, e)

        documents.append(
            DocumentUploadResponse(
                id=doc.id,
                filename=doc.filename,
                institution=doc.institution,
                document_type=doc.document_type,
                confidence_score=float(doc.confidence_score) if doc.confidence_score else None,
                uploaded_at=doc.uploaded_at,
            )
        )

    # Run matching
    matches_found = 0
    try:
        all_accounts = db.query(Account).all()
        if len(all_accounts) > 1:
            evidences = match_accounts(db, all_accounts)
            matches_found = len(evidences)
            group_accounts_into_persons(db, all_accounts)
    except Exception as e:
        logger.error("Matching failed: %s", e)

    db.commit()

    return MultiUploadResponse(
        documents=documents,
        matches_found=matches_found,
        duplicates=duplicates,
    )
