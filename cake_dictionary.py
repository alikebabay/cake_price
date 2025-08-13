# cake_dictionary.py
from typing import Final, Mapping, Set
import json, re, unicodedata
from importlib.resources import files

#нормализатор ввода пользователя
def _norm(s: str) -> str:
    # same as you had, but with NFKC to normalize Unicode
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    # keep letters/digits and currency symbols
    return re.sub(r"[^A-ZА-Я0-9$₽¥₼€£]", "", s)

#алаясы для всех валют мира
def _load_aliases() -> dict[str, list[str]]:
    text = files("cake_data").joinpath("aliases.json").read_text("utf-8")
    return json.loads(text)  # {"USD": ["USD","$","ДОЛЛАР",...], ...}

_RAW = _load_aliases()


# exactly your popular set (leave as-is)
POPULAR_CURRENCIES: Final[Set[str]] = {"USD", "BYN", "UAH", "RUB", "KGS", "UZS", "CNY"}

# --- Построение словаря «нормализованный алиас» -> «ISO-код» ---
# ВАЖНО: строим из _RAW (из JSON), а не из _CURRENCY_ALIASES (его тут нет).
_alias_map: dict[str, str] = {
    _norm(alias): code
    for code, aliases in _RAW.items()
    for alias in aliases
}

# Каждому коду добавим соответствие на самого себя (USD->USD и т.п.)
_alias_map.update({code: code for code in _RAW.keys()})

# Итоговая неизменяемая «публичная» мапа для импорта в main.py
ALIAS_TO_CODE: Final[Mapping[str, str]] = _alias_map

# --- Слова для выхода/отмены в одном месте ---
CANCEL_ALIASES: Final[Set[str]] = {_norm(x) for x in ["EXIT", "ВЫХОД", "ОТМЕНА", "CANCEL"]}

# --- Ровно как у тебя: принимаем любые 3 латинские буквы как ISO-код ---
def _try_iso_code(key: str) -> str | None:
    return key if re.fullmatch(r"[A-Z]{3}", key) else None