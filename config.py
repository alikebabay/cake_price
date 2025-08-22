import os
import sys
from pathlib import Path
from typing import Final

# Базовая цена торта
CAKE_PRICE_KZT: Final[float] = 600_000

# Источник UNECE
UNECE_YEAR = 2024
UNECE_UNIT = "USD"

# Убираем @ в начале username
def _normalize_username(s: str | None) -> str:
    s = (s or "").strip()
    return s[1:] if s.startswith("@") else s

# TOKEN и BOT_USERNAME из окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    token_file = os.getenv("TELEGRAM_TOKEN_FILE")
    if token_file and Path(token_file).exists():
        TOKEN = Path(token_file).read_text().strip()

BOT_USERNAME = _normalize_username(os.getenv("BOT_USERNAME"))

def assert_required():
    if not TOKEN:
        print("FATAL: TELEGRAM_TOKEN is not set (env or secret).", file=sys.stderr)
        sys.exit(1)