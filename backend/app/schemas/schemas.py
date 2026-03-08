from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# --- Document ---

class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    institution: str | None = None
    document_type: str | None = None
    confidence_score: float | None = None
    uploaded_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentUploadResponse):
    person_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    raw_extracted: str | None = None


# --- Holding ---

class HoldingResponse(BaseModel):
    id: str
    account_id: str
    document_id: str
    period: date
    stock_ticker: str
    stock_name: str | None = None
    volume: int = 0
    avg_price: Decimal | None = None
    close_price: Decimal | None = None
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None

    model_config = {"from_attributes": True}


# --- Transaction ---

class TransactionResponse(BaseModel):
    id: str
    account_id: str
    document_id: str
    date: date
    description: str | None = None
    amount: Decimal = Decimal("0")
    type: str
    category: str | None = None
    balance_after: Decimal | None = None
    institution: str | None = None

    model_config = {"from_attributes": True}


class PaginatedTransactionsResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Account ---

class CashBalanceResponse(BaseModel):
    id: str
    period: date
    balance: Decimal

    model_config = {"from_attributes": True}


class AccountResponse(BaseModel):
    id: str
    institution: str
    account_type: str
    account_number: str | None = None
    sid: str | None = None
    ksei_number: str | None = None
    currency: str = "IDR"
    holdings: list[HoldingResponse] = []
    cash_balances: list[CashBalanceResponse] = []

    model_config = {"from_attributes": True}


# --- Person ---

class PersonResponse(BaseModel):
    id: str
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    created_at: datetime
    accounts: list[AccountResponse] = []

    model_config = {"from_attributes": True}


# --- Consolidated Portfolio ---

class BrokerBreakdown(BaseModel):
    institution: str
    account_id: str
    volume: int
    avg_price: Decimal | None = None
    market_value: Decimal | None = None


class ConsolidatedHolding(BaseModel):
    stock_ticker: str
    stock_name: str | None = None
    total_volume: int = 0
    weighted_avg_price: Decimal | None = None
    close_price: Decimal | None = None
    total_market_value: Decimal | None = None
    total_unrealized_pnl: Decimal | None = None
    broker_breakdown: list[BrokerBreakdown] = []


class ConsolidatedPortfolioResponse(BaseModel):
    person_id: str
    total_portfolio_value: Decimal = Decimal("0")
    total_cash: Decimal = Decimal("0")
    holdings: list[ConsolidatedHolding] = []


# --- Dashboard ---

class DashboardSummaryResponse(BaseModel):
    net_worth: Decimal = Decimal("0")
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    asset_allocation: dict[str, Decimal] = Field(default_factory=dict)
    broker_allocation: dict[str, Decimal] = Field(default_factory=dict)


class MonthlyCashFlow(BaseModel):
    month: str  # YYYY-MM
    income: Decimal = Decimal("0")
    expense: Decimal = Decimal("0")
    net: Decimal = Decimal("0")


class CashFlowResponse(BaseModel):
    months: list[MonthlyCashFlow] = []
    total_income: Decimal = Decimal("0")
    total_expense: Decimal = Decimal("0")


# --- Upload ---

class MultiUploadResponse(BaseModel):
    documents: list[DocumentUploadResponse]
    matches_found: int = 0
    duplicates: list[dict] = []  # [{"filename": str, "existing_document_id": str}]


# --- Settings ---

class SettingResponse(BaseModel):
    key: str
    value: str | None
    encrypted: bool = False


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, str]


class GmailTestRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class GmailTestResponse(BaseModel):
    success: bool
    message: str


class GmailSearchRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    keywords: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    max_results: int = 50


class GmailSearchResult(BaseModel):
    message_id: str
    subject: str
    sender: str
    date: str
    attachments: list[dict]  # [{"filename": str, "size": int, "saved_path": str}]


class GmailSearchResponse(BaseModel):
    results: list[GmailSearchResult]
    total_pdfs: int


class GmailImportRequest(BaseModel):
    file_paths: list[str]
