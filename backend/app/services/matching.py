"""
Account matching engine.

Scores pairs of accounts to determine if they belong to the same person.
Scoring signals:
  - Exact name match:     +40
  - Fuzzy name (>85%):    +30
  - Same SID:             +50
  - Same email:           +45
  - Same phone:           +45
  - Same KSEI:            +50
  - Address similarity:   +20
  - Stock overlap:        +10 per overlapping stock

Thresholds:
  - >= 50: auto-merge
  - 30-49: suggest review
  - < 30:  separate
"""

import json
import logging
from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models.models import Account, Holding, MatchEvidence, Person

logger = logging.getLogger(__name__)

AUTO_MERGE_THRESHOLD = 40
SUGGEST_THRESHOLD = 25


def _normalize(value: str | None) -> str:
    """Normalize a string for comparison."""
    if not value:
        return ""
    return value.strip().lower().replace("-", "").replace(" ", "")


def _fuzzy_ratio(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 to 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _get_account_name(account: Account) -> str | None:
    """Extract the display name from account metadata."""
    if account.person and account.person.display_name:
        return account.person.display_name

    if account.metadata_json:
        try:
            meta = json.loads(account.metadata_json)
            name = meta.get("name") or meta.get("card_holder") or meta.get("account_holder") or meta.get("client_name")
            # Filter out obviously wrong names (table headers etc.)
            if name and len(name) < 50 and not any(kw in name.upper() for kw in ["NOTASI", "KETERANGAN", "REKENING"]):
                return name
        except (json.JSONDecodeError, AttributeError):
            pass
    return None


def _get_account_metadata(account: Account, key: str) -> str | None:
    """Get a metadata value from account."""
    if account.metadata_json:
        try:
            meta = json.loads(account.metadata_json)
            return meta.get(key)
        except (json.JSONDecodeError, AttributeError):
            pass
    return None


def _get_holdings_tickers(account: Account) -> set[str]:
    """Get set of stock tickers held in an account."""
    return {h.stock_ticker.upper() for h in account.holdings if h.stock_ticker}


def _score_pair(account_a: Account, account_b: Account) -> list[tuple[str, str, int]]:
    """
    Score a pair of accounts. Returns list of (signal_type, signal_value, score).
    """
    signals: list[tuple[str, str, int]] = []

    # Name matching
    name_a = _get_account_name(account_a)
    name_b = _get_account_name(account_b)
    if name_a and name_b:
        norm_a = _normalize(name_a)
        norm_b = _normalize(name_b)
        if norm_a and norm_b:
            if norm_a == norm_b:
                signals.append(("exact_name", f"{name_a} == {name_b}", 40))
            else:
                ratio = _fuzzy_ratio(name_a, name_b)
                if ratio > 0.85:
                    signals.append(("fuzzy_name", f"{name_a} ~= {name_b} ({ratio:.0%})", 30))

    # SID matching
    if account_a.sid and account_b.sid:
        if _normalize(account_a.sid) == _normalize(account_b.sid):
            signals.append(("same_sid", account_a.sid, 50))

    # Email matching
    email_a = _get_account_metadata(account_a, "email")
    email_b = _get_account_metadata(account_b, "email")
    if not email_a and account_a.person:
        email_a = account_a.person.email
    if not email_b and account_b.person:
        email_b = account_b.person.email
    if email_a and email_b:
        if _normalize(email_a) == _normalize(email_b):
            signals.append(("same_email", email_a, 45))

    # Phone matching
    phone_a = _get_account_metadata(account_a, "phone")
    phone_b = _get_account_metadata(account_b, "phone")
    if not phone_a and account_a.person:
        phone_a = account_a.person.phone
    if not phone_b and account_b.person:
        phone_b = account_b.person.phone
    if phone_a and phone_b:
        if _normalize(phone_a) == _normalize(phone_b):
            signals.append(("same_phone", phone_a, 45))

    # KSEI matching
    if account_a.ksei_number and account_b.ksei_number:
        if _normalize(account_a.ksei_number) == _normalize(account_b.ksei_number):
            signals.append(("same_ksei", account_a.ksei_number, 50))

    # Address similarity
    addr_a = _get_account_metadata(account_a, "address")
    addr_b = _get_account_metadata(account_b, "address")
    if addr_a and addr_b:
        ratio = _fuzzy_ratio(addr_a, addr_b)
        if ratio > 0.7:
            signals.append(("address_similarity", f"{ratio:.0%}", 20))

    # Stock overlap
    tickers_a = _get_holdings_tickers(account_a)
    tickers_b = _get_holdings_tickers(account_b)
    overlap = tickers_a & tickers_b
    if overlap:
        overlap_score = min(len(overlap) * 10, 50)  # Cap at 50
        signals.append(("stock_overlap", ",".join(sorted(overlap)), overlap_score))

    return signals


def match_accounts(db: Session, accounts: list[Account]) -> list[MatchEvidence]:
    """
    Compare all pairs of accounts and create MatchEvidence records.
    Returns list of created MatchEvidence objects.
    """
    evidences: list[MatchEvidence] = []

    for i in range(len(accounts)):
        for j in range(i + 1, len(accounts)):
            a, b = accounts[i], accounts[j]

            # Skip if same institution and same account
            if a.institution == b.institution and a.account_number == b.account_number:
                continue

            signals = _score_pair(a, b)
            total_score = sum(s[2] for s in signals)

            if total_score >= SUGGEST_THRESHOLD:
                for signal_type, signal_value, score in signals:
                    evidence = MatchEvidence(
                        account_a_id=a.id,
                        account_b_id=b.id,
                        signal_type=signal_type,
                        signal_value=signal_value,
                        score=score,
                        confirmed=total_score >= AUTO_MERGE_THRESHOLD,
                    )
                    db.add(evidence)
                    evidences.append(evidence)

    db.flush()
    return evidences


def group_accounts_into_persons(db: Session, accounts: list[Account]) -> list[Person]:
    """
    Group accounts into persons based on match evidence.
    Auto-merged accounts (score >= 50) are grouped under the same person.
    """
    # Build adjacency map from auto-confirmed matches
    groups: dict[str, set[str]] = defaultdict(set)
    for account in accounts:
        groups[account.id].add(account.id)

    # Find all confirmed match evidences
    account_ids = [a.id for a in accounts]
    evidences = (
        db.query(MatchEvidence)
        .filter(
            MatchEvidence.confirmed == True,  # noqa: E712
            MatchEvidence.account_a_id.in_(account_ids),
            MatchEvidence.account_b_id.in_(account_ids),
        )
        .all()
    )

    # Union-find style grouping
    parent: dict[str, str] = {a.id: a.id for a in accounts}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for ev in evidences:
        if ev.account_a_id in parent and ev.account_b_id in parent:
            union(ev.account_a_id, ev.account_b_id)

    # Group accounts by root
    account_map = {a.id: a for a in accounts}
    person_groups: dict[str, list[Account]] = defaultdict(list)
    for account in accounts:
        root = find(account.id)
        person_groups[root].append(account)

    # Create or update persons
    persons: list[Person] = []
    for group_accounts in person_groups.values():
        # Check if any account already has a person
        existing_person = None
        for acc in group_accounts:
            if acc.person_id:
                existing_person = db.query(Person).get(acc.person_id)
                if existing_person:
                    break

        if not existing_person:
            # Create new person from best available account data
            name = None
            email = None
            phone = None
            for acc in group_accounts:
                acc_name = _get_account_name(acc)
                if acc_name and (not name or len(acc_name) < len(name)):
                    name = acc_name
                if not email:
                    email = _get_account_metadata(acc, "email")
                if not phone:
                    phone = _get_account_metadata(acc, "phone")

            existing_person = Person(
                display_name=name,
                email=email,
                phone=phone,
            )
            db.add(existing_person)
            db.flush()

        # Assign all accounts to this person
        for acc in group_accounts:
            acc.person_id = existing_person.id

        persons.append(existing_person)

    db.flush()
    return persons
