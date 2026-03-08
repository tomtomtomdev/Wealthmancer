"""
Transaction auto-categorization using keyword matching.

Maps known Indonesian merchants and keywords to spending categories.
"""

import re

# Keyword -> category mapping (case-insensitive matching)
# More specific patterns first to avoid false matches
_CATEGORY_RULES: list[tuple[str, str]] = [
    # Food & Beverage
    (r"GRAB\s*FOOD", "Food & Beverage"),
    (r"GOFOOD", "Food & Beverage"),
    (r"SHOPEE\s*FOOD", "Food & Beverage"),
    (r"MC\s*DONALD", "Food & Beverage"),
    (r"MCDONALD", "Food & Beverage"),
    (r"KFC", "Food & Beverage"),
    (r"STARBUCKS", "Food & Beverage"),
    (r"CHATIME", "Food & Beverage"),
    (r"HOKBEN", "Food & Beverage"),
    (r"PIZZA\s*HUT", "Food & Beverage"),
    (r"BURGER\s*KING", "Food & Beverage"),
    (r"J\.?CO", "Food & Beverage"),
    (r"FORE\s*COFFEE", "Food & Beverage"),
    (r"KOPI\s*KENANGAN", "Food & Beverage"),
    (r"RESTORAN", "Food & Beverage"),
    (r"RESTAURANT", "Food & Beverage"),
    (r"CAFE", "Food & Beverage"),
    (r"WARUNG", "Food & Beverage"),
    (r"BAKSO", "Food & Beverage"),

    # Groceries
    (r"ASTRO", "Groceries"),
    (r"SEGARI", "Groceries"),
    (r"SAYURBOX", "Groceries"),
    (r"HYPERMART", "Groceries"),
    (r"SUPERINDO", "Groceries"),
    (r"RANCH\s*MARKET", "Groceries"),
    (r"FARMERS\s*MARKET", "Groceries"),
    (r"ALFAMART", "Groceries"),
    (r"INDOMARET", "Groceries"),
    (r"GIANT", "Groceries"),
    (r"CARREFOUR", "Groceries"),
    (r"TRANSMART", "Groceries"),
    (r"LOTTE\s*MART", "Groceries"),
    (r"HERO", "Groceries"),

    # Transport
    (r"GRAB(?!\s*FOOD)", "Transport"),
    (r"GOJEK", "Transport"),
    (r"GORIDE", "Transport"),
    (r"GOCAR", "Transport"),
    (r"UBER", "Transport"),
    (r"BLUE\s*BIRD", "Transport"),
    (r"TRANSJAKARTA", "Transport"),
    (r"MRT", "Transport"),
    (r"KRL", "Transport"),
    (r"COMMUTER", "Transport"),
    (r"PERTAMINA", "Transport"),
    (r"SHELL", "Transport"),
    (r"BP\s*AKR", "Transport"),
    (r"TOTAL\s*ENERGI", "Transport"),
    (r"PARKIR", "Transport"),
    (r"PARKING", "Transport"),
    (r"TOLL|TOL\s", "Transport"),

    # Shopping
    (r"SHOPEE(?!\s*FOOD)", "Shopping"),
    (r"TOKOPEDIA", "Shopping"),
    (r"LAZADA", "Shopping"),
    (r"BUKALAPAK", "Shopping"),
    (r"BLIBLI", "Shopping"),
    (r"ZALORA", "Shopping"),
    (r"UNIQLO", "Shopping"),
    (r"H&M|H\s*AND\s*M", "Shopping"),
    (r"ZARA", "Shopping"),
    (r"MATAHARI", "Shopping"),
    (r"MAP", "Shopping"),
    (r"ACE\s*HARDWARE", "Shopping"),

    # Health
    (r"SILOAM", "Health"),
    (r"HALODOC", "Health"),
    (r"ALODOKTER", "Health"),
    (r"APOTEK", "Health"),
    (r"PHARMACY", "Health"),
    (r"KIMIA\s*FARMA", "Health"),
    (r"GUARDIAN", "Health"),
    (r"WATSON", "Health"),
    (r"RUMAH\s*SAKIT", "Health"),
    (r"RS\s+\w+", "Health"),
    (r"KLINIK", "Health"),
    (r"HOSPITAL", "Health"),
    (r"BPJS\s*KESEHATAN", "Health"),

    # Transfer / E-wallet
    (r"DANA\b", "Transfer"),
    (r"OVO", "Transfer"),
    (r"GOPAY", "Transfer"),
    (r"LINK\s*AJA", "Transfer"),
    (r"FLIP", "Transfer"),
    (r"TRANSFER", "Transfer"),
    (r"TRF\b", "Transfer"),
    (r"TRSF", "Transfer"),
    (r"RTGS", "Transfer"),
    (r"BI\s*FAST", "Transfer"),

    # Bills & Utilities
    (r"PLN", "Utilities"),
    (r"LISTRIK", "Utilities"),
    (r"PDAM", "Utilities"),
    (r"AIR\s*BERSIH", "Utilities"),
    (r"TELKOM", "Utilities"),
    (r"INDIHOME", "Utilities"),
    (r"WIFI", "Utilities"),
    (r"INTERNET", "Utilities"),
    (r"PULSA", "Utilities"),
    (r"TELKOMSEL", "Utilities"),
    (r"XL\s*AXIATA", "Utilities"),
    (r"INDOSAT", "Utilities"),
    (r"SMARTFREN", "Utilities"),
    (r"TRI\b", "Utilities"),

    # Entertainment
    (r"NETFLIX", "Entertainment"),
    (r"SPOTIFY", "Entertainment"),
    (r"YOUTUBE", "Entertainment"),
    (r"DISNEY", "Entertainment"),
    (r"VIDIO", "Entertainment"),
    (r"CINEMA", "Entertainment"),
    (r"CGV", "Entertainment"),
    (r"XXI", "Entertainment"),
    (r"CINEPOLIS", "Entertainment"),
    (r"STEAM", "Entertainment"),
    (r"PLAYSTATION", "Entertainment"),
    (r"APPLE\.COM", "Entertainment"),
    (r"GOOGLE\s*PLAY", "Entertainment"),

    # Insurance
    (r"ASURANSI", "Insurance"),
    (r"INSURANCE", "Insurance"),
    (r"PRUDENTIAL", "Insurance"),
    (r"ALLIANZ", "Insurance"),
    (r"AXA", "Insurance"),
    (r"MANULIFE", "Insurance"),
    (r"BPJS\s*KETENAGAKERJAAN", "Insurance"),

    # Education
    (r"SEKOLAH", "Education"),
    (r"UNIVERSITAS", "Education"),
    (r"SCHOOL", "Education"),
    (r"RUANGGURU", "Education"),
    (r"ZENIUS", "Education"),
    (r"UDEMY", "Education"),
    (r"COURSERA", "Education"),

    # Investment
    (r"BIBIT", "Investment"),
    (r"BAREKSA", "Investment"),
    (r"AJAIB", "Investment"),
    (r"STOCKBIT", "Investment"),
    (r"SEKURITAS", "Investment"),
    (r"REKSADANA", "Investment"),
    (r"MUTUAL\s*FUND", "Investment"),

    # Income
    (r"GAJI", "Income"),
    (r"SALARY", "Income"),
    (r"PAYROLL", "Income"),
    (r"DIVIDEN", "Income"),
    (r"DIVIDEND", "Income"),
    (r"BUNGA", "Income"),
    (r"INTEREST", "Income"),
    (r"CASHBACK", "Income"),

    # ATM
    (r"ATM", "ATM Withdrawal"),
    (r"TARIK\s*TUNAI", "ATM Withdrawal"),
    (r"CASH\s*WITHDRAWAL", "ATM Withdrawal"),

    # Tax
    (r"PAJAK", "Tax"),
    (r"TAX", "Tax"),

    # Fee
    (r"ADMIN", "Fee"),
    (r"BIAYA", "Fee"),
    (r"FEE", "Fee"),
    (r"CHARGE", "Fee"),
]

# Pre-compile patterns
_COMPILED_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pattern, re.IGNORECASE), category)
    for pattern, category in _CATEGORY_RULES
]


def categorize_transaction(description: str) -> str | None:
    """
    Categorize a transaction based on its description using keyword matching.

    Returns the category string or None if no match is found.
    """
    if not description:
        return None

    for pattern, category in _COMPILED_RULES:
        if pattern.search(description):
            return category

    return None


def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """
    Categorize a list of transaction dicts in-place.
    Each dict should have a 'description' key.
    Adds a 'category' key to each transaction.
    """
    for txn in transactions:
        desc = txn.get("description", "")
        txn["category"] = categorize_transaction(desc)
    return transactions
