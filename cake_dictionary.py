# cake_dictionary.py
from typing import Final, Mapping, Set, Optional
import json, re, unicodedata
from importlib.resources import files

#нормализатор ввода пользователя
def _norm(s: str) -> str:
    # same as you had, but with NFKC to normalize Unicode
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    # keep letters/digits and currency symbols
    return re.sub(r"[^A-ZА-Я0-9$₽¥₼€£]", "", s)

#маппер валюта-страна мира
def _load_ccy_to_iso3() -> dict[str, str]:
    text = files("cake_data").joinpath("currency_to_iso3.json").read_text("utf-8")
    raw = json.loads(text)
    # защитимся от мусора и приведём к верхнему регистру
    return {
        (k or "").strip().upper(): (v or "").strip().upper()
        for k, v in raw.items()
        if isinstance(k, str) and isinstance(v, str) and len(k) == 3 and len(v) == 3
    }

#алаясы для всех валют мира
def _load_aliases() -> dict[str, list[str]]:
    text = files("cake_data").joinpath("aliases.json").read_text("utf-8")
    return json.loads(text)  # {"USD": ["USD","$","ДОЛЛАР",...], ...}

_RAW = _load_aliases()
_CCY_TO_ISO3 = _load_ccy_to_iso3()


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

def currency_to_iso3(ccy: str | None) -> Optional[str]:
    """Возвращает ISO3 домашней страны по коду валюты (читает cake_data/currency_to_iso3.json)."""
    if not ccy:
        return None
    return _CCY_TO_ISO3.get(ccy.strip().upper())

def resolve_country_iso3_from_user_input(raw: str) -> Optional[str]:
    """
    Алиас/название/ISO валюты -> код валюты -> ISO3 страны.
    Пример: 'амер' -> USD -> USA.
    """
    key = _norm(raw)
    code = ALIAS_TO_CODE.get(key) or _try_iso_code(key)
    return currency_to_iso3(code) if code else None