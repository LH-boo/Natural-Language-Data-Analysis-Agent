import os
import time
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
SAMPLE_DIR = BASE_DIR / "sample_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

METADATA_DATABASE_URL = os.getenv(
    "METADATA_DATABASE_URL", f"sqlite:///{(DATA_DIR / 'metadata.db').as_posix()}"
)
DUCKDB_PATH = os.getenv("DUCKDB_PATH", str(DATA_DIR / "analytics.duckdb"))

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "90"))

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "500"))
QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT", "30"))
MAX_REPAIR = int(os.getenv("MAX_REPAIR", "2"))

APP_NAME = "自然语言数据分析 Agent"
APP_VERSION = "1.0.0"
APP_START_TIME = time.time()
