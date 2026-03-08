#!/bin/bash
set -e

echo "============================================"
echo "  Wealthmancer - Financial Document Manager"
echo "============================================"
echo ""

# Detect OS
OS="$(uname -s)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running with Docker or locally
USE_DOCKER=false
if command -v docker &>/dev/null && command -v docker compose &>/dev/null; then
    USE_DOCKER=true
fi

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    print_status "Created .env from template"
    print_warn "Optional: Add ANTHROPIC_API_KEY to .env for Vision LLM extraction"
    echo ""
fi

# Create data directories
mkdir -p uploads data

if [ "$USE_DOCKER" = true ] && [ "$1" != "--local" ]; then
    echo "Starting with Docker..."
    echo ""
    docker compose up --build -d
    echo ""
    print_status "Wealthmancer is running!"
else
    echo "Starting locally (no Docker)..."
    echo ""

    # Check Python - need 3.12 specifically (3.14 breaks pydantic)
    PYTHON_CMD=""
    if command -v python3.12 &>/dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3 &>/dev/null; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        if [ "$PY_VER" = "3.12" ] || [ "$PY_VER" = "3.13" ]; then
            PYTHON_CMD="python3"
        else
            print_warn "Python $PY_VER detected but 3.12 is required (3.14 breaks pydantic)"
            if [ "$OS" = "Darwin" ] && command -v brew &>/dev/null; then
                print_warn "Installing Python 3.12 via Homebrew..."
                brew install python@3.12
                PYTHON_CMD="python3.12"
            else
                print_error "Please install Python 3.12: https://python.org"
                exit 1
            fi
        fi
    else
        print_error "Python 3 is required. Install Python 3.12 from https://python.org"
        exit 1
    fi
    print_status "Using $($PYTHON_CMD --version)"

    # Check Node
    if ! command -v node &>/dev/null; then
        print_error "Node.js is required. Install from https://nodejs.org"
        exit 1
    fi

    # Check poppler (needed for pdf2image)
    if [ "$OS" = "Darwin" ]; then
        if ! command -v pdftotext &>/dev/null; then
            print_warn "Installing poppler (needed for PDF processing)..."
            brew install poppler
        fi
    elif [ "$OS" = "Linux" ]; then
        if ! command -v pdftotext &>/dev/null; then
            print_warn "Installing poppler-utils..."
            sudo apt-get install -y poppler-utils
        fi
    fi

    # Backend setup
    echo "Setting up backend..."
    cd backend

    # Recreate venv if it exists with wrong Python version
    if [ -d .venv ]; then
        VENV_PY_VER=$(.venv/bin/python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
        if [ "$VENV_PY_VER" != "3.12" ] && [ "$VENV_PY_VER" != "3.13" ]; then
            print_warn "Existing venv uses Python $VENV_PY_VER, recreating with $PYTHON_CMD..."
            rm -rf .venv
        fi
    fi

    $PYTHON_CMD -m venv .venv 2>/dev/null || true
    source .venv/bin/activate
    pip install -r requirements.txt -q
    print_status "Backend dependencies installed"

    # Start backend in background
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    BACKEND_PID=$!
    cd ..

    # Frontend setup
    echo "Setting up frontend..."
    cd frontend
    npm install --silent
    print_status "Frontend dependencies installed"

    # Start frontend
    npm run dev &
    FRONTEND_PID=$!
    cd ..

    print_status "Backend PID: $BACKEND_PID"
    print_status "Frontend PID: $FRONTEND_PID"

    # Trap to clean up on exit
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

    echo ""
    print_status "Wealthmancer is running!"
fi

echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "  Upload your financial PDFs at http://localhost:3000/upload"
echo ""

# If running locally, wait for processes
if [ "$USE_DOCKER" != true ] || [ "$1" = "--local" ]; then
    echo "Press Ctrl+C to stop..."
    wait
fi
