# Wealthmancer

A full-stack app that extracts financial data from Indonesian bank and brokerage PDF statements, identifies accounts belonging to the same person, and presents a consolidated financial picture through charts and tables.

## Supported Institutions

| Institution | Type |
|---|---|
| CIMB Niaga | Credit Card |
| BCA Sekuritas | Securities |
| Mandiri Sekuritas | Securities |
| BNI Sekuritas | Securities |
| Stockbit | Securities |
| BCA | Bank |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, SQLite
- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **PDF Processing:** pdfplumber, pdf2image, Claude Vision API (optional)

## How It Works

1. **Upload** — Drop in PDF statements from any supported institution
2. **Extract** — A 3-tier pipeline processes each PDF:
   - Text + regex extraction (fast, free)
   - OCR extraction (fallback)
   - Claude Vision API (highest accuracy, requires API key)
3. **Match** — Accounts are linked to the same person using name, SID, email, phone, and stock overlap signals
4. **View** — Dashboard shows consolidated holdings, net worth, and per-account breakdowns

## Quick Start

```bash
git clone <repo-url> && cd wealthmancer
cp .env.example .env          # optionally add ANTHROPIC_API_KEY
./setup.sh                    # Docker (auto-detected) or local
```

For local-only (no Docker):

```bash
./setup.sh --local
```

### Prerequisites (local)

- Python 3.12 or 3.13
- Node.js (v20+)
- poppler (`brew install poppler` on macOS, `apt install poppler-utils` on Linux)

### Manual Start

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

## Configuration

Copy `.env.example` to `.env`:

```env
DATABASE_URL=sqlite:///./data/wealthmancer.db
UPLOAD_DIR=./uploads
ANTHROPIC_API_KEY=              # optional, enables Vision LLM extraction
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Project Structure

```
wealthmancer/
├── backend/
│   └── app/
│       ├── main.py                    # FastAPI entrypoint
│       └── services/extraction/
│           └── templates/             # Per-institution extractors
│               ├── bca_bank.py
│               ├── bca_sekuritas.py
│               ├── bni_sekuritas.py
│               ├── cimb_niaga.py
│               ├── mandiri_sekuritas.py
│               └── stockbit.py
├── frontend/                          # Next.js app
├── docker-compose.yml
├── setup.sh
└── SPEC.md
```
