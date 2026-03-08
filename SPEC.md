# Wealthmancer - Financial Document Consolidation App

## Overview

A full-stack application that uses ML/vision to extract financial data from Indonesian bank and brokerage PDF statements, identifies accounts belonging to the same person, consolidates holdings across providers, and presents the unified financial picture through beautiful charts and tables.

---

## Document Analysis (from provided samples)

### Document Types Identified

| # | File | Institution | Type | Key Data |
|---|------|-------------|------|----------|
| 1 | `credit card billing statement_17-02-2026_551291790.pdf` | **CIMB Niaga** | Credit Card Statement | MC Gold Reguler, card ending 8086, balance IDR 4,247,403 |
| 2 | `24NP_soa310126.pdf` | **BCA Sekuritas** | Securities Statement of Account | Account 24NP, SID IDD0705UU759746, zero balance |
| 3 | `CS260131-M359B21C-20260202095517750.pdf` | **Mandiri Sekuritas** | Client Statement + Portfolio | Client M359B21C, 10 stocks, cost IDR 3,421,000 / market IDR 2,486,400 |
| 4 | `SOA_23AA40752_JAN2026.PDF.pdf` | **BNI Sekuritas** | Consolidated Account Statement | User 23AA40752, cash IDR 104,737, 2 stocks, total asset IDR 1,326,737 |
| 5 | `0088552_soa300126_170351.pdf` | **Stockbit** | Statement of Account + Portfolio | Client 0088552, cash IDR 70,601, 5 stocks, portfolio IDR 982,001 |
| 6 | `0160135654Apr2025.pdf` | **BCA** | Bank Statement (Rekening Tahapan) | Account 0160135654, 12 pages of transactions |

### Account Matching Signals Discovered

These are the real linkage signals found across the 6 documents:

| Signal Type | Value | Found In |
|-------------|-------|----------|
| **Name** | TOMMY YOHANES | All 6 documents |
| **Email** | tommy.yohanes@gmail.com | BCA Sekuritas, Mandiri Sekuritas, Stockbit |
| **Phone** | +6281285965506 | BCA Sekuritas, Mandiri Sekuritas, Stockbit |
| **SID** | IDD0705UU759746 | BCA Sekuritas, Stockbit |
| **SID** | IDD0705LBQ91836 | Mandiri Sekuritas, BNI Sekuritas |
| **Address** | Jl. Cendana Icon Plaza no. 23, Tangerang | Mandiri Sekuritas, BNI Sekuritas |
| **Overlapping stocks** | ADMF | Mandiri Sekuritas, BNI Sekuritas |
| **Overlapping stocks** | DLTA | Mandiri Sekuritas, BNI Sekuritas, Stockbit |
| **Overlapping stocks** | SIDO | Mandiri Sekuritas, Stockbit |
| **Overlapping stocks** | BFIN | Mandiri Sekuritas, Stockbit |
| **Bank account** | BCA 4959393190 | BCA Sekuritas (linked bank) |
| **Bank account** | BCA 4996784347 | Stockbit (linked bank) |

---

## Architecture

```
+---------------------------------------------------+
|                  Frontend (Next.js)                |
|                                                    |
|  +------------+ +-------------+ +---------------+  |
|  | Upload &   | | Dashboard   | | Consolidated  |  |
|  | Processing | | Charts      | | Tables        |  |
|  +------------+ +-------------+ +---------------+  |
|        |               ^               ^            |
+--------|---------------|---------------|------------+
         v               |               |
+---------------------------------------------------+
|                Backend (FastAPI)                    |
|                                                    |
|  +-------------+ +------------+ +--------------+   |
|  | PDF Vision  | | Account    | | Portfolio     |  |
|  | Extraction  | | Matching   | | Consolidation |  |
|  +-------------+ +------------+ +--------------+   |
|        |               |               |            |
+--------|---------------|---------------|------------+
         v               v               v
+---------------------------------------------------+
|              Database (SQLite/PostgreSQL)           |
|  documents | accounts | holdings | transactions    |
+---------------------------------------------------+
```

### Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Frontend** | Next.js 14 + TypeScript | App router, RSC, great DX |
| **Charts** | Recharts + Tremor | Beautiful financial charts out of the box |
| **Tables** | TanStack Table + Tailwind | Sortable, filterable, responsive |
| **Styling** | Tailwind CSS + shadcn/ui | Polished financial dashboard look |
| **Backend** | Python FastAPI | Best ML/vision ecosystem |
| **PDF Vision/ML** | See ML Pipeline below | Multi-strategy extraction |
| **Database** | SQLite (dev) / PostgreSQL (prod) | SQLAlchemy ORM |
| **Task Queue** | Celery + Redis (optional) | For async PDF processing |

---

## ML/Vision Pipeline

PDF extraction is the hardest problem here. Each institution uses different layouts, fonts, and structures. A multi-strategy pipeline handles this:

### Strategy 1: Vision LLM (Primary)
- Send each PDF page as an image to a vision model (Claude / GPT-4V / local LLaVA)
- Structured prompt asks for specific fields per document type
- Returns JSON with extracted fields
- **Pros**: Handles any layout, understands context, reads Indonesian text
- **Cons**: API cost, latency

### Strategy 2: Document AI / Layout-aware OCR (Fallback)
- **pdf2image** + **PaddleOCR** or **EasyOCR** (good for Indonesian text)
- **LayoutLMv3** or **DocTR** for table structure detection
- Custom post-processing per institution template
- **Pros**: Runs locally, no API cost, fast
- **Cons**: Needs template tuning per institution

### Strategy 3: Text-based Extraction (Fast path)
- **pdfplumber** / **camelot** for PDFs with embedded text (not scanned)
- Regex-based field extraction per known institution template
- **Pros**: Fastest, most accurate for text-based PDFs
- **Cons**: Breaks on scanned/image PDFs

### Pipeline Flow

```
PDF Upload
    |
    v
[Text extraction attempt via pdfplumber]
    |
    +-- Has embedded text? --> Strategy 3 (regex templates)
    |                              |
    |                              +-- Confidence < 80%? --> Strategy 1 (Vision LLM)
    |
    +-- Scanned/image PDF? --> Strategy 2 (OCR + Layout)
                                   |
                                   +-- Confidence < 80%? --> Strategy 1 (Vision LLM)
```

### Institution Detection (Classifier)

A lightweight classifier identifies the institution before extraction:

```python
# Features used for classification:
# - Logo detection (template matching or embeddings)
# - Header text patterns ("CIMB NIAGA", "BCA sekuritas", "mandiri sekuritas", etc.)
# - Layout fingerprinting (column positions, table structures)
# - Filename patterns (SOA_, CS_, credit card billing, etc.)
```

Once institution is identified, the appropriate extraction template is applied.

### Extracted Data Schema per Document Type

**Credit Card Statement** (CIMB Niaga):
```json
{
  "institution": "CIMB Niaga",
  "document_type": "credit_card_statement",
  "account_holder": "TOMMY YOHANES",
  "card_type": "MC GOLD REGULER",
  "card_number_masked": "5481 17XX XXXX 8086",
  "statement_date": "2026-02-17",
  "due_date": "2026-03-05",
  "credit_limit": 28000000,
  "current_balance": 4247403.83,
  "minimum_payment": 212371.00,
  "transactions": [
    {"date": "2026-01-20", "description": "SHOPEE Jakarta", "amount": 56000.00, "type": "debit"},
    ...
  ]
}
```

**Securities Statement** (BCA Sekuritas / Mandiri / BNI / Stockbit):
```json
{
  "institution": "Mandiri Sekuritas",
  "document_type": "securities_statement",
  "account_holder": "TOMMY YOHANES",
  "client_id": "M359B21C",
  "sid": "IDD0705LBQ91836",
  "ksei_no": "CC0018IP900187",
  "email": "tommy.yohanes@gmail.com",
  "phone": "+6281285965506",
  "period": "2026-01",
  "cash_balance": 0,
  "portfolio": [
    {"stock_id": "ADMF", "volume": 100, "avg_price": 13700, "close_price": 8300, "market_value": 830000, "unrealized_pnl": -540000},
    ...
  ],
  "total_portfolio_cost": 3421000,
  "total_market_value": 2486400,
  "total_unrealized_pnl": -934600
}
```

**Bank Statement** (BCA):
```json
{
  "institution": "BCA",
  "document_type": "bank_statement",
  "account_holder": "TOMMY YOHANES",
  "account_number": "0160135654",
  "period": "2025-04",
  "currency": "IDR",
  "opening_balance": 8966158.15,
  "transactions": [
    {"date": "2025-04-01", "description": "TRSF E-BANKING DB - ASTRO", "amount": 128500.00, "type": "debit", "balance": 8837658.15},
    ...
  ]
}
```

---

## Account Matching Engine

### Matching Algorithm

Uses a weighted scoring system to determine if accounts belong to the same person:

```
Score Components:
  - Exact name match:           +40 points
  - Fuzzy name match (>85%):    +30 points
  - Same SID:                   +50 points (definitive)
  - Same email:                 +45 points (near-definitive)
  - Same phone:                 +45 points (near-definitive)
  - Same KSEI number:           +50 points (definitive)
  - Address similarity (>80%):  +20 points
  - Overlapping stock holdings: +10 points per overlap

Threshold:
  >= 50 points  -->  Auto-merge (same person, high confidence)
  30-49 points  -->  Suggest merge (ask user to confirm)
  < 30 points   -->  Separate accounts
```

### Consolidation Logic

After matching, the system consolidates:

1. **Stock Holdings**: Merge same ticker across brokerages
   - e.g., DLTA: 100 shares (Mandiri) + 200 shares (BNI) + 100 shares (Stockbit) = 400 shares total
   - Weighted average cost basis calculated across brokers

2. **Cash Positions**: Sum across all accounts
   - Securities cash: BCA Sek (0) + Mandiri Sek (0) + BNI Sek (104,737) + Stockbit (70,601) = IDR 175,338
   - Bank cash: BCA (balance from statement)

3. **Liabilities**: Credit card balances
   - CIMB Niaga CC: IDR 4,247,404

4. **Net Worth**: Total assets - Total liabilities

---

## Frontend Design

### Pages & Components

#### 1. Upload Page (`/upload`)
- Drag-and-drop zone for multiple PDFs
- Real-time processing status per file (uploading -> extracting -> matching -> done)
- Preview of extracted data before confirming
- Manual correction UI if extraction confidence is low

#### 2. Dashboard (`/dashboard`)
- **Net Worth Summary Card** - total assets, liabilities, net worth in large font
- **Asset Allocation Donut Chart** - stocks vs cash vs other, by percentage
- **Net Worth Over Time** - line chart (as more statements are uploaded over time)
- **Broker Allocation Bar Chart** - how assets are split across Mandiri, BNI, Stockbit, etc.
- **Top Holdings Treemap** - visual block size by market value
- **Monthly Cash Flow** - income vs spending from bank statements (bar chart)
- **Spending Category Breakdown** - pie chart from credit card + bank transactions (Shopee, Grab, etc.)

#### 3. Portfolio Page (`/portfolio`)
- **Consolidated Holdings Table**:
  | Stock | Total Shares | Avg Cost | Current Price | Market Value | Unrealized P&L | % of Portfolio | Brokers |
  |-------|-------------|----------|---------------|-------------|---------------|----------------|---------|
  | DLTA  | 400         | 2,060    | 1,960        | 784,000     | -134,000      | 17.5%          | Mandiri, BNI, Stockbit |
  | ADMF  | 200         | 13,700   | 8,300        | 1,660,000   | -1,080,000    | 37.1%          | Mandiri, BNI |
  | ...   |             |          |               |             |               |                |         |

- Expandable rows showing per-broker breakdown
- Sort by any column, filter by broker
- Export to CSV/Excel

#### 4. Transactions Page (`/transactions`)
- Unified transaction feed across all accounts
- Filterable by: date range, institution, type (debit/credit), category
- Auto-categorization of spending (food, transport, shopping, bills)
- Search functionality

#### 5. Accounts Page (`/accounts`)
- List of all detected accounts with institution logos
- Account linking UI (confirm/reject auto-matches)
- Per-account detail view

### Chart Library Details

Using **Recharts** (React-based) + **Tremor** (pre-built dashboard components):

- Donut charts for allocation
- Area/line charts for time series
- Bar charts for comparisons
- Treemaps for holdings visualization
- Sparklines in table cells for mini-trends
- Color theme: dark mode financial dashboard (navy/slate background, green for gains, red for losses)

---

## Database Schema

```sql
-- People (matched identity)
CREATE TABLE persons (
    id UUID PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Source documents
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    person_id UUID REFERENCES persons(id),
    filename TEXT NOT NULL,
    institution TEXT NOT NULL,       -- 'cimb_niaga', 'bca_sekuritas', 'mandiri_sekuritas', etc.
    document_type TEXT NOT NULL,     -- 'credit_card', 'securities', 'bank_statement'
    period_start DATE,
    period_end DATE,
    raw_extracted JSON,             -- full ML extraction output
    confidence_score FLOAT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Financial accounts
CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    person_id UUID REFERENCES persons(id),
    institution TEXT NOT NULL,
    account_type TEXT NOT NULL,      -- 'credit_card', 'securities', 'bank'
    account_number TEXT,
    sid TEXT,                        -- Securities Investor ID (for matching)
    ksei_number TEXT,
    currency TEXT DEFAULT 'IDR',
    metadata JSON
);

-- Stock holdings (per account, per period)
CREATE TABLE holdings (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    document_id UUID REFERENCES documents(id),
    period DATE NOT NULL,
    stock_ticker TEXT NOT NULL,
    stock_name TEXT,
    volume INTEGER,
    avg_price DECIMAL(15,2),
    close_price DECIMAL(15,2),
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2)
);

-- Cash balances (per account, per period)
CREATE TABLE cash_balances (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    document_id UUID REFERENCES documents(id),
    period DATE NOT NULL,
    balance DECIMAL(15,2)
);

-- Transactions (credit card + bank)
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    account_id UUID REFERENCES accounts(id),
    document_id UUID REFERENCES documents(id),
    date DATE NOT NULL,
    description TEXT,
    amount DECIMAL(15,2),
    type TEXT,                      -- 'debit' or 'credit'
    category TEXT,                  -- auto-categorized
    balance_after DECIMAL(15,2),
    metadata JSON
);

-- Account matching evidence
CREATE TABLE match_evidence (
    id UUID PRIMARY KEY,
    account_a UUID REFERENCES accounts(id),
    account_b UUID REFERENCES accounts(id),
    signal_type TEXT,               -- 'name', 'sid', 'email', 'phone', 'address', 'stock_overlap'
    signal_value TEXT,
    score INTEGER,
    confirmed BOOLEAN DEFAULT FALSE
);
```

---

## API Endpoints

```
POST   /api/upload              Upload PDF(s), triggers extraction pipeline
GET    /api/documents           List all uploaded documents
GET    /api/documents/:id       Get extraction result for a document

GET    /api/persons             List matched persons
GET    /api/persons/:id         Get person detail with all accounts

GET    /api/accounts            List all accounts
GET    /api/accounts/:id        Account detail with holdings + transactions

GET    /api/portfolio/consolidated    Consolidated holdings across all brokers
GET    /api/portfolio/by-broker       Holdings grouped by broker

GET    /api/transactions        Unified transaction list (filterable)
GET    /api/dashboard/summary   Net worth, asset allocation, key metrics
GET    /api/dashboard/cashflow  Monthly income/expense aggregation

POST   /api/match/confirm       Confirm or reject a suggested account match
POST   /api/reprocess/:id       Re-run extraction on a document
```

---

## Project Structure

```
wealthmancer/
+-- backend/
|   +-- app/
|   |   +-- main.py                  # FastAPI app entry
|   |   +-- config.py                # Settings & env vars
|   |   +-- models/                  # SQLAlchemy models
|   |   +-- schemas/                 # Pydantic request/response schemas
|   |   +-- api/
|   |   |   +-- upload.py
|   |   |   +-- documents.py
|   |   |   +-- portfolio.py
|   |   |   +-- transactions.py
|   |   |   +-- dashboard.py
|   |   +-- services/
|   |   |   +-- extraction/
|   |   |   |   +-- pipeline.py      # Orchestrator (pick strategy)
|   |   |   |   +-- vision_llm.py    # Strategy 1: Claude/GPT-4V
|   |   |   |   +-- ocr_layout.py    # Strategy 2: PaddleOCR + LayoutLM
|   |   |   |   +-- text_regex.py    # Strategy 3: pdfplumber + regex
|   |   |   |   +-- templates/       # Per-institution extraction templates
|   |   |   |       +-- cimb_niaga.py
|   |   |   |       +-- bca_sekuritas.py
|   |   |   |       +-- mandiri_sekuritas.py
|   |   |   |       +-- bni_sekuritas.py
|   |   |   |       +-- stockbit.py
|   |   |   |       +-- bca_bank.py
|   |   |   +-- matching.py          # Account matching engine
|   |   |   +-- consolidation.py     # Portfolio consolidation logic
|   |   |   +-- categorization.py    # Transaction auto-categorization
|   |   +-- db/
|   |       +-- database.py
|   |       +-- migrations/
|   +-- requirements.txt
|   +-- Dockerfile
|
+-- frontend/
|   +-- src/
|   |   +-- app/
|   |   |   +-- page.tsx             # Landing / redirect to dashboard
|   |   |   +-- upload/page.tsx
|   |   |   +-- dashboard/page.tsx
|   |   |   +-- portfolio/page.tsx
|   |   |   +-- transactions/page.tsx
|   |   |   +-- accounts/page.tsx
|   |   +-- components/
|   |   |   +-- charts/
|   |   |   |   +-- AssetAllocationDonut.tsx
|   |   |   |   +-- NetWorthLine.tsx
|   |   |   |   +-- BrokerAllocationBar.tsx
|   |   |   |   +-- HoldingsTreemap.tsx
|   |   |   |   +-- CashFlowBar.tsx
|   |   |   |   +-- SpendingPie.tsx
|   |   |   +-- tables/
|   |   |   |   +-- HoldingsTable.tsx
|   |   |   |   +-- TransactionsTable.tsx
|   |   |   +-- upload/
|   |   |   |   +-- DropZone.tsx
|   |   |   |   +-- ProcessingStatus.tsx
|   |   |   +-- ui/                  # shadcn/ui components
|   |   +-- lib/
|   |       +-- api.ts               # API client
|   |       +-- formatters.ts        # IDR currency, date formatting
|   +-- package.json
|   +-- tailwind.config.ts
|   +-- Dockerfile
|
+-- setup.sh                         # 1-step install & run script
+-- docker-compose.yml               # Full stack orchestration
+-- SPEC.md                          # This file
```

---

## 1-Step Install & Run

### `setup.sh`

```bash
#!/bin/bash
set -e

echo "=== Wealthmancer Setup ==="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker required. Install: https://docker.com"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose required."; exit 1; }

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from template. Edit it to add your API keys (optional)."
    echo "  ANTHROPIC_API_KEY=   (for Vision LLM extraction - recommended)"
    echo "  OPENAI_API_KEY=      (alternative Vision LLM)"
    echo ""
    echo "Without API keys, the app will use local OCR only (less accurate)."
fi

# Build and start
docker compose up --build -d

echo ""
echo "=== Wealthmancer is running! ==="
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Upload your financial PDFs at http://localhost:3000/upload"
```

### `docker-compose.yml`

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes: ["./uploads:/app/uploads", "./data:/app/data"]
    env_file: .env
    environment:
      - DATABASE_URL=sqlite:///./data/wealthmancer.db

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [backend]
```

**Usage:**
```bash
git clone <repo> && cd wealthmancer && ./setup.sh
```

---

## Implementation Phases

### Phase 1: Core Extraction (Week 1-2)
- [ ] Backend scaffold (FastAPI + SQLite + models)
- [ ] Text-based extraction (Strategy 3) for all 6 institution templates
- [ ] Institution auto-detection from PDF content/filename
- [ ] Upload API endpoint with extraction pipeline
- [ ] Basic frontend: upload page with drag-and-drop

### Phase 2: ML/Vision + Matching (Week 3-4)
- [ ] Vision LLM integration (Claude API with document images)
- [ ] OCR fallback with PaddleOCR for scanned documents
- [ ] Confidence scoring and strategy fallback logic
- [ ] Account matching engine (name, SID, email, phone scoring)
- [ ] Manual match confirmation UI

### Phase 3: Consolidation + Dashboard (Week 5-6)
- [ ] Portfolio consolidation service (merge holdings across brokers)
- [ ] Transaction categorization (Shopee=shopping, Grab=transport, etc.)
- [ ] Dashboard page with all charts (Recharts + Tremor)
- [ ] Consolidated holdings table with per-broker expansion
- [ ] Net worth calculation

### Phase 4: Polish + Advanced (Week 7-8)
- [ ] Transaction search and filtering
- [ ] CSV/Excel export
- [ ] Dark mode financial theme
- [ ] Docker setup and 1-step install script
- [ ] Handle edge cases (multi-page statements, partial extraction)
- [ ] Period-over-period comparison charts

---

## Key Design Decisions

1. **Vision LLM as primary extractor**: Indonesian financial documents have inconsistent layouts, mixed Bahasa/English, and varied table structures. Vision models handle this far better than rule-based parsing. Text extraction (Strategy 3) is used as a fast path when PDFs have embedded text.

2. **SID as the strongest matching signal**: Indonesian securities accounts share a Securities Investor ID (SID) across brokerages registered under the same KSEI identity. Two different SIDs (IDD0705UU759746 and IDD0705LBQ91836) suggest the user has accounts under two KSEI sub-accounts, but name + email + phone confirm they are the same person.

3. **SQLite for simplicity**: Single-user personal finance tool doesn't need PostgreSQL. SQLite keeps the 1-step install simple (no database server). Can upgrade to Postgres via SQLAlchemy if needed.

4. **Per-institution templates**: Each Indonesian financial institution has a distinct PDF format. Maintaining separate extraction templates (even when using Vision LLM) provides structured prompts that dramatically improve extraction accuracy.

5. **Confidence-based fallback**: Rather than picking one extraction strategy, the pipeline tries the fastest approach first and falls back to more expensive methods only when confidence is low. This minimizes API costs while maintaining accuracy.
