# cake_dictionary.py
from typing import Final, Mapping, Set
import re
import unicodedata

def _norm(s: str) -> str:
    # same as you had, but with NFKC to normalize Unicode
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    # keep letters/digits and currency symbols
    s = re.sub(r"[^A-ZА-Я0-9$₽¥₼€£]", "", s)
    return s

# exactly your popular set (leave as-is)
POPULAR_CURRENCIES: Final[Set[str]] = {"USD", "BYN", "UAH", "RUB", "KGS", "UZS", "CNY"}

# your aliases (raw), unchanged
_CURRENCY_ALIASES = {
    "USD": ["USD", "$", "ДОЛЛАР", "ДОЛЛ.", "БАКС", "БАКСЫ", "АМЕРИКАНСКИЙДОЛЛАР"],
    "BYN": ["BYN", "БЕЛРУБ", "БЕЛ.РУБЛЬ", "БЕЛОРУССКИЙРУБЛЬ"],
    "UAH": ["UAH", "ГРИВНА", "ГРН", "УКРАИНСКАЯГРИВНА"],
    "RUB": ["RUB", "РУБ", "РУБЛЬ", "₽", "РОССИЙСКИЙРУБЛЬ", "RUR"],
    "KGS": ["KGS", "СОМ", "КЫРГЫЗСКИЙСОМ"],
    "UZS": ["UZS", "СУМ", "УЗБЕКСКИЙСУМ"],
    "CNY": ["CNY", "ЮАНЬ", "КИТАЙСКИЙЮАНЬ", "¥", "RMB"],
}

# Build with NORMALIZED KEYS so aliases like "ДОЛЛ." match after _norm -> "ДОЛЛ"
_alias_pairs = (
    (_norm(alias), code)
    for code, aliases in _CURRENCY_ALIASES.items()
    for alias in aliases
)
ALIAS_TO_CODE: Final[Mapping[str, str]] = {
    **{k: v for k, v in _alias_pairs},
    **{code: code for code in POPULAR_CURRENCIES},  # ensure ISO codes map to themselves
}

CANCEL_ALIASES: Final[Set[str]] = {_norm(x) for x in ["EXIT", "ВЫХОД", "ОТМЕНА", "CANCEL"]}

def _try_iso_code(key: str) -> str | None:
    # accept any 3-letter Latin ISO 4217 code
    return key if re.fullmatch(r"[A-Z]{3}", key) else None