import os
import sys
from pathlib import Path
from typing import Final

# базовая цена торта. Пока константа
CAKE_PRICE_KZT: Final[float] = 600_000

def _normalize_username(s: str | None) -> str:
    s = (s or "").strip()
    return s[1:] if s.startswith("@") else s

# TELEGRAM_TOKEN из окружения или из Docker secret-файла
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    token_file = os.getenv("TELEGRAM_TOKEN_FILE")
    if token_file and Path(token_file).exists():
        TOKEN = Path(token_file).read_text().strip()

BOT_USERNAME = _normalize_username(os.getenv("BOT_USERNAME"))

# В Cloud Run есть env K_SERVICE — используем /tmp
if os.getenv("K_SERVICE"):
    default_db = "/tmp/exchange_rates.db"
else:
    default_db = str(Path(__file__).with_name("exchange_rates.db"))

# Путь к БД
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).with_name("exchange_rates.db")))

def assert_required():
    if not TOKEN:
        print("FATAL: TELEGRAM_TOKEN is not set (env or secret).", file=sys.stderr)
        sys.exit(1)