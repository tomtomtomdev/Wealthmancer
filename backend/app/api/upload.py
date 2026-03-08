"""
Upload API router.

Handles PDF upload, extraction, and document management.
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.db.database import get_db
from app.models.models import Account, CashBalance, Document, Holding, Person, Transaction
from app.schemas.schemas import DocumentDetailResponse, DocumentUploadResponse, MultiUploadResponse
from app.services.categorization import categorize_transaction
from app.services.extraction.pipeline import extract_document
from app.services.matching import group_accounts_into_persons, match_accounts

logger = logging.getLogger(__name__)

router = APIRouter()


def _parse_date_str(date_str: str | None) -> date | None:
    """Parse an ISO date string to a date object."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return None


def _store_extraction_results(
    db: Session,
    document: Document,
    extraction: dict,
) -> list[Account]:
    """Store extracted data as database records. Returns created accounts."""
    data = extraction.get("data", {})
    institution = extraction.get("institution")
    doc_type = extraction.get("document_type")
    created_accounts: list[Account] = []

    if not data or not institution:
        return created_accounts

    # Determine account type from document type
    account_type = "unknown"
    if doc_type in ("credit_card_statement",):
        account_type = "credit_card"
    elif doc_type in ("securities_statement", "securities_portfolio", "securities_consolidated"):
        account_type = "securities"
    elif doc_type in ("bank_statement",):
        account_type = "bank"

    # Build metadata from extracted info
    metadata: dict = {}
    for key in ["account_holder", "name", "card_holder", "email", "phone", "address",
                 "client_id", "bank_account", "bank", "mtbi_account", "ae_name",
                 "card_type", "card_number"]:
        if key in data and data[key]:
            metadata[key] = data[key]

    # Find or create account
    account_number = data.get("account_number") or data.get("client_id") or data.get("card_number")
    sid = data.get("sid")
    ksei = data.get("ksei")

    # Check for existing account
    existing_account = None
    if account_number:
        existing_account = (
            db.query(Account)
            .filter(Account.institution == institution, Account.account_number == account_number)
            .first()
        )
    if not existing_account and sid:
        existing_account = (
            db.query(Account)
            .filter(Account.sid == sid)
            .first()
        )

    if existing_account:
        account = existing_account
        # Update SID, KSEI if newly extracted
        if sid and not account.sid:
            account.sid = sid
        if ksei and not account.ksei_number:
            account.ksei_number = ksei
        if account_number and not account.account_number:
            account.account_number = account_number
        # Update metadata
        if account.metadata_json:
            try:
                old_meta = json.loads(account.metadata_json)
                old_meta.update(metadata)
                metadata = old_meta
            except json.JSONDecodeError:
                pass
        account.metadata_json = json.dumps(metadata)
    else:
        account = Account(
            institution=institution,
            account_type=account_type,
            account_number=account_number,
            sid=sid,
            ksei_number=ksei,
            currency=data.get("currency", "IDR"),
            metadata_json=json.dumps(metadata),
        )
        db.add(account)
        db.flush()
        created_accounts.append(account)

    # Assign document to account's person
    if account.person_id:
        document.person_id = account.person_id

    # Store portfolio holdings
    portfolio = data.get("portfolio", [])
    period = _parse_date_str(extraction.get("period_end")) or date.today()

    for item in portfolio:
        ticker = item.get("stock_id") or item.get("stock_ticker") or item.get("stock_name", "").split()[0] if item.get("stock_name") else None
        if not ticker:
            continue

        holding = Holding(
            account_id=account.id,
            document_id=document.id,
            period=period,
            stock_ticker=ticker.upper(),
            stock_name=item.get("stock_name"),
            volume=int(item.get("volume", 0) or item.get("available_volume", 0) or item.get("quantity", 0)),
            avg_price=item.get("avg_price") or item.get("buying_price"),
            close_price=item.get("close_price") or item.get("closing_price"),
            market_value=item.get("market_value"),
            unrealized_pnl=item.get("unrealized_pnl") or item.get("unrealized_gain_loss_rp"),
        )
        db.add(holding)

    # Store cash balance
    cash_balance_val = data.get("cash_balance") or data.get("cash")
    if cash_balance_val is not None:
        cash = CashBalance(
            account_id=account.id,
            document_id=document.id,
            period=period,
            balance=cash_balance_val,
        )
        db.add(cash)

    # Store cash summary entries
    for cash_entry in data.get("cash_summary", []):
        if cash_entry.get("balance") is not None:
            cash = CashBalance(
                account_id=account.id,
                document_id=document.id,
                period=period,
                balance=cash_entry["balance"],
            )
            db.add(cash)

    # Store transactions
    transactions = data.get("transactions", [])
    for txn_data in transactions:
        txn_date = _parse_date_str(txn_data.get("date"))
        if not txn_date:
            continue

        description = txn_data.get("description", "")
        amount = txn_data.get("amount", 0)
        txn_type = txn_data.get("type", "debit")

        # For BCA bank statements with separate debit/credit amounts
        if txn_data.get("debit") and not txn_data.get("credit"):
            txn_type = "debit"
            amount = txn_data["debit"]
        elif txn_data.get("credit") and not txn_data.get("debit"):
            txn_type = "credit"
            amount = txn_data["credit"]

        category = categorize_transaction(description)

        txn = Transaction(
            account_id=account.id,
            document_id=document.id,
            date=txn_date,
            description=description,
            amount=abs(amount) if amount else 0,
            type=txn_type,
            category=category,
            balance_after=txn_data.get("balance") or txn_data.get("ending_balance") or txn_data.get("balance_after"),
        )
        db.add(txn)

    db.flush()
    return created_accounts


@router.post("/upload", response_model=MultiUploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or more PDF files for extraction and processing."""
    documents: list[DocumentUploadResponse] = []
    duplicates: list[dict] = []
    all_new_accounts: list[Account] = []

    for file in files:
        if not file.filename:
            continue

        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")

        # Save file to disk
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Calculate SHA256 hash for dedup
        file_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicate
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc:
            duplicates.append({
                "filename": file.filename,
                "existing_document_id": existing_doc.id,
            })
            # Remove the newly saved file
            try:
                os.remove(file_path)
            except OSError:
                pass
            continue

        # Run extraction pipeline
        try:
            extraction = await extract_document(file_path)
        except Exception as e:
            logger.error("Extraction failed for %s: %s", file.filename, e)
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
            filename=file.filename,
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
            logger.error("Failed to store extraction results for %s: %s", file.filename, e)

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

    # Run matching on ALL accounts (not just new ones)
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

    return MultiUploadResponse(documents=documents, matches_found=matches_found, duplicates=duplicates)


@router.get("/documents", response_model=list[DocumentUploadResponse])
async def list_documents(db: Session = Depends(get_db)):
    """List all uploaded documents."""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    return [
        DocumentUploadResponse(
            id=doc.id,
            filename=doc.filename,
            institution=doc.institution,
            document_type=doc.document_type,
            confidence_score=float(doc.confidence_score) if doc.confidence_score else None,
            uploaded_at=doc.uploaded_at,
        )
        for doc in docs
    ]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document detail with extraction result."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        institution=doc.institution,
        document_type=doc.document_type,
        confidence_score=float(doc.confidence_score) if doc.confidence_score else None,
        uploaded_at=doc.uploaded_at,
        person_id=doc.person_id,
        period_start=doc.period_start,
        period_end=doc.period_end,
        raw_extracted=doc.raw_extracted,
    )


@router.post("/reprocess/{document_id}", response_model=DocumentUploadResponse)
async def reprocess_document(document_id: str, db: Session = Depends(get_db)):
    """Re-run extraction on an existing document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Find the file on disk
    # Look for file matching the document ID pattern
    file_path = None
    for fname in os.listdir(UPLOAD_DIR):
        if doc.filename in fname:
            file_path = os.path.join(UPLOAD_DIR, fname)
            break

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Original file not found on disk")

    # Clear old extraction data
    db.query(Holding).filter(Holding.document_id == doc.id).delete()
    db.query(CashBalance).filter(CashBalance.document_id == doc.id).delete()
    db.query(Transaction).filter(Transaction.document_id == doc.id).delete()

    # Re-run extraction
    extraction = await extract_document(file_path)

    doc.institution = extraction.get("institution")
    doc.document_type = extraction.get("document_type")
    doc.period_start = _parse_date_str(extraction.get("period_start"))
    doc.period_end = _parse_date_str(extraction.get("period_end"))
    doc.raw_extracted = json.dumps(extraction.get("data", {}))
    doc.confidence_score = extraction.get("confidence_score", 0.0)

    _store_extraction_results(db, doc, extraction)
    db.commit()

    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        institution=doc.institution,
        document_type=doc.document_type,
        confidence_score=float(doc.confidence_score) if doc.confidence_score else None,
        uploaded_at=doc.uploaded_at,
    )
