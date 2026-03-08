"""
Transactions API router.

Provides unified, filterable, paginated transaction listing.
"""

import logging
import math
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Account, Transaction
from app.schemas.schemas import PaginatedTransactionsResponse, TransactionResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/transactions", response_model=PaginatedTransactionsResponse)
async def list_transactions(
    date_from: date | None = Query(None, description="Filter start date (inclusive)"),
    date_to: date | None = Query(None, description="Filter end date (inclusive)"),
    institution: str | None = Query(None, description="Filter by institution name"),
    type: str | None = Query(None, description="Filter by type: debit or credit"),
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in transaction description"),
    person_id: str | None = Query(None, description="Filter by person ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    List transactions with filtering and pagination.
    Joins across accounts to include institution info.
    """
    query = db.query(Transaction).join(Account, Transaction.account_id == Account.id)

    # Apply filters
    if date_from:
        query = query.filter(Transaction.date >= date_from)
    if date_to:
        query = query.filter(Transaction.date <= date_to)
    if institution:
        query = query.filter(Account.institution.ilike(f"%{institution}%"))
    if type:
        query = query.filter(Transaction.type == type.lower())
    if category:
        query = query.filter(Transaction.category.ilike(f"%{category}%"))
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))
    if person_id:
        query = query.filter(Account.person_id == person_id)

    # Get total count
    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))

    # Apply pagination and ordering
    transactions = (
        query.order_by(Transaction.date.desc(), Transaction.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Build response with institution info
    items: list[TransactionResponse] = []
    for txn in transactions:
        account = db.query(Account).filter(Account.id == txn.account_id).first()
        items.append(
            TransactionResponse(
                id=txn.id,
                account_id=txn.account_id,
                document_id=txn.document_id,
                date=txn.date,
                description=txn.description,
                amount=txn.amount,
                type=txn.type,
                category=txn.category,
                balance_after=txn.balance_after,
                institution=account.institution if account else None,
            )
        )

    return PaginatedTransactionsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
