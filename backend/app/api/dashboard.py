"""
Dashboard API router.

Provides summary metrics and cash flow analysis.
"""

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Account, CashBalance, Holding, Person, Transaction
from app.schemas.schemas import (
    CashFlowResponse,
    DashboardSummaryResponse,
    MonthlyCashFlow,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_default_person(db: Session) -> Person | None:
    return db.query(Person).order_by(Person.created_at).first()


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    person_id: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Dashboard summary: net worth, total assets, liabilities,
    asset allocation, and broker allocation.
    """
    if not person_id:
        person = _get_default_person(db)
        if not person:
            return DashboardSummaryResponse()
        person_id = person.id

    accounts = db.query(Account).filter(Account.person_id == person_id).all()

    total_assets = Decimal("0")
    total_liabilities = Decimal("0")
    asset_allocation: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    broker_allocation: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

    for account in accounts:
        if account.account_type == "credit_card":
            # Credit card balance is a liability
            if account.cash_balances:
                latest = max(account.cash_balances, key=lambda cb: cb.period)
                total_liabilities += Decimal(str(abs(latest.balance)))
        else:
            # Securities and bank accounts are assets
            # Cash balances
            if account.cash_balances:
                latest_cash = max(account.cash_balances, key=lambda cb: cb.period)
                cash_val = Decimal(str(latest_cash.balance))
                total_assets += cash_val
                asset_allocation["Cash"] += cash_val
                broker_allocation[account.institution] += cash_val

            # Holdings market value
            seen_tickers: set[str] = set()
            sorted_holdings = sorted(account.holdings, key=lambda h: h.period, reverse=True)
            for holding in sorted_holdings:
                ticker = holding.stock_ticker.upper()
                if ticker not in seen_tickers:
                    seen_tickers.add(ticker)
                    if holding.market_value:
                        mv = Decimal(str(holding.market_value))
                        total_assets += mv
                        asset_allocation["Equities"] += mv
                        broker_allocation[account.institution] += mv

    net_worth = total_assets - total_liabilities

    return DashboardSummaryResponse(
        net_worth=net_worth,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        asset_allocation=dict(asset_allocation),
        broker_allocation=dict(broker_allocation),
    )


@router.get("/dashboard/cashflow", response_model=CashFlowResponse)
async def get_cash_flow(
    person_id: str | None = None,
    months: int = Query(12, ge=1, le=60, description="Number of months to show"),
    db: Session = Depends(get_db),
):
    """
    Monthly cash flow from bank and credit card transactions.
    Income = credit transactions, Expense = debit transactions.
    """
    if not person_id:
        person = _get_default_person(db)
        if not person:
            return CashFlowResponse()
        person_id = person.id

    accounts = db.query(Account).filter(Account.person_id == person_id).all()
    account_ids = [a.id for a in accounts]

    if not account_ids:
        return CashFlowResponse()

    transactions = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids))
        .order_by(Transaction.date)
        .all()
    )

    # Group by month
    monthly: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"income": Decimal("0"), "expense": Decimal("0")}
    )

    for txn in transactions:
        month_key = txn.date.strftime("%Y-%m")
        amount = Decimal(str(abs(txn.amount)))

        if txn.type == "credit":
            # Exclude transfers and investment-related credits from income
            if txn.category not in ("Transfer", "Investment", "ATM Withdrawal"):
                monthly[month_key]["income"] += amount
        else:
            # Exclude transfers from expenses
            if txn.category not in ("Transfer", "Investment"):
                monthly[month_key]["expense"] += amount

    # Sort by month and limit
    sorted_months = sorted(monthly.keys(), reverse=True)[:months]
    sorted_months.reverse()

    total_income = Decimal("0")
    total_expense = Decimal("0")
    result_months: list[MonthlyCashFlow] = []

    for month_key in sorted_months:
        data = monthly[month_key]
        income = data["income"]
        expense = data["expense"]
        total_income += income
        total_expense += expense

        result_months.append(
            MonthlyCashFlow(
                month=month_key,
                income=income,
                expense=expense,
                net=income - expense,
            )
        )

    return CashFlowResponse(
        months=result_months,
        total_income=total_income,
        total_expense=total_expense,
    )
