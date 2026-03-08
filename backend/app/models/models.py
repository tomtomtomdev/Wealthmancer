import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="person", cascade="all, delete-orphan")
    documents: Mapped[list["Document"]] = relationship("Document", back_populates="person", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    person_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("persons.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(512))
    institution: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_extracted: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)  # SHA256 hash of file content
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    person: Mapped["Person | None"] = relationship("Person", back_populates="documents")
    holdings: Mapped[list["Holding"]] = relationship("Holding", back_populates="document", cascade="all, delete-orphan")
    cash_balances: Mapped[list["CashBalance"]] = relationship("CashBalance", back_populates="document", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="document", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    person_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("persons.id"), nullable=True)
    institution: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(50))  # securities, bank, credit_card
    account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sid: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ksei_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="IDR")
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    person: Mapped["Person | None"] = relationship("Person", back_populates="accounts")
    holdings: Mapped[list["Holding"]] = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
    cash_balances: Mapped[list["CashBalance"]] = relationship("CashBalance", back_populates="account", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    match_evidences_a: Mapped[list["MatchEvidence"]] = relationship(
        "MatchEvidence", foreign_keys="MatchEvidence.account_a_id", back_populates="account_a_rel", cascade="all, delete-orphan"
    )
    match_evidences_b: Mapped[list["MatchEvidence"]] = relationship(
        "MatchEvidence", foreign_keys="MatchEvidence.account_b_id", back_populates="account_b_rel", cascade="all, delete-orphan"
    )


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    period: Mapped[date] = mapped_column(Date)
    stock_ticker: Mapped[str] = mapped_column(String(20))
    stock_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    close_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unrealized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)

    account: Mapped["Account"] = relationship("Account", back_populates="holdings")
    document: Mapped["Document"] = relationship("Document", back_populates="holdings")


class CashBalance(Base):
    __tablename__ = "cash_balances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    period: Mapped[date] = mapped_column(Date)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)

    account: Mapped["Account"] = relationship("Account", back_populates="cash_balances")
    document: Mapped["Document"] = relationship("Document", back_populates="cash_balances")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"))
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    type: Mapped[str] = mapped_column(String(10))  # debit or credit
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    account: Mapped["Account"] = relationship("Account", back_populates="transactions")
    document: Mapped["Document"] = relationship("Document", back_populates="transactions")


class MatchEvidence(Base):
    __tablename__ = "match_evidences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    account_a_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"))
    account_b_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"))
    signal_type: Mapped[str] = mapped_column(String(50))
    signal_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    account_a_rel: Mapped["Account"] = relationship("Account", foreign_keys=[account_a_id], back_populates="match_evidences_a")
    account_b_rel: Mapped["Account"] = relationship("Account", foreign_keys=[account_b_id], back_populates="match_evidences_b")
