"""
Portfolio API router.

Provides consolidated and per-broker portfolio views.
"""

import logging
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Account, Holding, Person
from app.schemas.schemas import ConsolidatedPortfolioResponse, HoldingResponse
from app.services.consolidation import consolidate_holdings

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_default_person(db: Session) -> Person | None:
    """Get the default person (first person, or None)."""
    return db.query(Person).order_by(Person.created_at).first()


@router.get("/portfolio/consolidated", response_model=ConsolidatedPortfolioResponse)
async def get_consolidated_portfolio(
    person_id: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Get consolidated holdings across all brokers.
    If person_id is not provided, uses the default (first) person.
    """
    if not person_id:
        person = _get_default_person(db)
        if not person:
            return ConsolidatedPortfolioResponse(
                person_id="",
                total_portfolio_value=Decimal("0"),
                total_cash=Decimal("0"),
                holdings=[],
            )
        person_id = person.id

    return consolidate_holdings(db, person_id)


@router.get("/portfolio/by-broker")
async def get_portfolio_by_broker(
    person_id: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Get holdings grouped by broker/institution.
    """
    if not person_id:
        person = _get_default_person(db)
        if not person:
            return {"brokers": []}
        person_id = person.id

    accounts = (
        db.query(Account)
        .filter(Account.person_id == person_id, Account.account_type == "securities")
        .all()
    )

    brokers: list[dict] = []
    for account in accounts:
        # Get latest holdings per ticker
        seen_tickers: set[str] = set()
        sorted_holdings = sorted(account.holdings, key=lambda h: h.period, reverse=True)
        latest_holdings: list[HoldingResponse] = []

        for holding in sorted_holdings:
            ticker = holding.stock_ticker.upper()
            if ticker not in seen_tickers:
                seen_tickers.add(ticker)
                latest_holdings.append(
                    HoldingResponse(
                        id=holding.id,
                        account_id=holding.account_id,
                        document_id=holding.document_id,
                        period=holding.period,
                        stock_ticker=holding.stock_ticker,
                        stock_name=holding.stock_name,
                        volume=holding.volume,
                        avg_price=holding.avg_price,
                        close_price=holding.close_price,
                        market_value=holding.market_value,
                        unrealized_pnl=holding.unrealized_pnl,
                    )
                )

        total_value = sum(
            Decimal(str(h.market_value)) for h in latest_holdings if h.market_value
        )

        brokers.append({
            "institution": account.institution,
            "account_id": account.id,
            "account_number": account.account_number,
            "total_value": total_value,
            "holdings": latest_holdings,
        })

    return {"brokers": brokers}
