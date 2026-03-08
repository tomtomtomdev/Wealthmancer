import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'wealthmancer.db'}")
ANTHROPIC_API_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))

# Ensure directories exist
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
data_dir = BASE_DIR / "data"
data_dir.mkdir(parents=True, exist_ok=True)
