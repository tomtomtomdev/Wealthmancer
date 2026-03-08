"""
Portfolio consolidation service.

Merges holdings of the same ticker across multiple broker accounts,
computes weighted average cost, sums cash, and calculates net worth.
"""

import logging
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.models import Account, CashBalance, Holding, Person
from app.schemas.schemas import (
    BrokerBreakdown,
    ConsolidatedHolding,
    ConsolidatedPortfolioResponse,
)

logger = logging.getLogger(__name__)


def consolidate_holdings(db: Session, person_id: str) -> ConsolidatedPortfolioResponse:
    """
    Consolidate all holdings across brokers for a person.

    - Merges same ticker across brokers using weighted average cost
    - Sums cash across all accounts
    - Calculates total portfolio value
    """
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        return ConsolidatedPortfolioResponse(
            person_id=person_id,
            total_portfolio_value=Decimal("0"),
            total_cash=Decimal("0"),
            holdings=[],
        )

    accounts = db.query(Account).filter(Account.person_id == person_id).all()

    # Gather all holdings grouped by ticker
    ticker_holdings: dict[str, list[tuple[Holding, Account]]] = defaultdict(list)
    for account in accounts:
        # Get latest holdings per ticker for this account
        seen_tickers: set[str] = set()
        # Sort by period descending to get latest
        sorted_holdings = sorted(account.holdings, key=lambda h: h.period, reverse=True)
        for holding in sorted_holdings:
            ticker = holding.stock_ticker.upper()
            if ticker not in seen_tickers:
                seen_tickers.add(ticker)
                ticker_holdings[ticker].append((holding, account))

    # Sum cash balances (latest per account)
    total_cash = Decimal("0")
    for account in accounts:
        if account.cash_balances:
            latest_cash = max(account.cash_balances, key=lambda cb: cb.period)
            total_cash += Decimal(str(latest_cash.balance))

    # Build consolidated holdings
    consolidated: list[ConsolidatedHolding] = []
    total_portfolio_value = Decimal("0")

    for ticker, holdings_with_accounts in sorted(ticker_holdings.items()):
        total_volume = 0
        total_cost = Decimal("0")
        total_market_value = Decimal("0")
        total_unrealized = Decimal("0")
        close_price: Decimal | None = None
        stock_name: str | None = None
        breakdowns: list[BrokerBreakdown] = []

        for holding, account in holdings_with_accounts:
            vol = holding.volume or 0
            avg = Decimal(str(holding.avg_price)) if holding.avg_price else Decimal("0")
            mv = Decimal(str(holding.market_value)) if holding.market_value else Decimal("0")
            pnl = Decimal(str(holding.unrealized_pnl)) if holding.unrealized_pnl else Decimal("0")

            total_volume += vol
            total_cost += avg * vol
            total_market_value += mv
            total_unrealized += pnl

            if holding.close_price:
                close_price = Decimal(str(holding.close_price))
            if holding.stock_name and not stock_name:
                stock_name = holding.stock_name

            breakdowns.append(
                BrokerBreakdown(
                    institution=account.institution,
                    account_id=account.id,
                    volume=vol,
                    avg_price=avg if avg else None,
                    market_value=mv if mv else None,
                )
            )

        weighted_avg = (total_cost / total_volume) if total_volume > 0 else None

        consolidated_holding = ConsolidatedHolding(
            stock_ticker=ticker,
            stock_name=stock_name,
            total_volume=total_volume,
            weighted_avg_price=weighted_avg,
            close_price=close_price,
            total_market_value=total_market_value if total_market_value else None,
            total_unrealized_pnl=total_unrealized if total_unrealized else None,
            broker_breakdown=breakdowns,
        )
        consolidated.append(consolidated_holding)
        total_portfolio_value += total_market_value

    return ConsolidatedPortfolioResponse(
        person_id=person_id,
        total_portfolio_value=total_portfolio_value,
        total_cash=total_cash,
        holdings=consolidated,
    )
