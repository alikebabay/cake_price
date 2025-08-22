# cake_dictionary.py  (простая версия)
import json, re, unicodedata
from pathlib import Path

# Где лежат json-файлы
DATA_DIR = Path(__file__).resolve().parent / "cake_data"

def _load_json(name: str):
    path = DATA_DIR / name
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# Нормализация
def _norm_ccy(s: str) -> str:
    # валюты: вверхний регистр, выкидываем всё кроме латинских букв/цифр/символов валют
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    return re.sub(r"[^A-ZА-Я0-9$₽¥₼€£]", "", s)

def _norm_country(s: str) -> str:
    # страны: вверхний регистр, схлопываем пробелы (знаки не трогаем — у тебя в json есть скобки)
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    return re.sub(r"\s+", " ", s)

# Загружаем данные
_aliases_raw              = _load_json("aliases.json")                 # {"USD": ["USD","$","ДОЛЛАР",...]} — ТОЛЬКО валюты
_ccy_to_iso3_raw          = _load_json("currency_to_iso3.json")        # {"USD":"USA", "KZT":"KAZ", ...} (ISO3 справа; null допускается)
_country_name_to_iso3_raw = _load_json("country_name_to_iso3.json")    # {"UNITED STATES":"USA", "БЕЛЬГИЯ":"BEL", "БЕЛГ":"BEL", ...}

# Строим: алиас валюты → код валюты
ALIAS_TO_CCY = {}
for code, aliases in (_aliases_raw or {}).items():
    if not isinstance(aliases, list):
        continue
    code_key = _norm_ccy(str(code))
    if not code_key:
        continue
    ALIAS_TO_CCY[code_key] = code_key  # сам код тоже алиас
    for a in aliases:
        if isinstance(a, str):
            k = _norm_ccy(a)
            if k:
                ALIAS_TO_CCY[k] = code_key

# Строим: ISO3 → базовая валюта страны (только если однозначно задана)
ISO3_TO_CCY = {}
for ccy, iso3 in (_ccy_to_iso3_raw or {}).items():
    if isinstance(ccy, str) and isinstance(iso3, str):
        c = ccy.strip().upper()
        i = iso3.strip().upper()
        if len(c) == 3 and len(i) == 3:
            ISO3_TO_CCY[i] = c

# Строим: название страны/алиас → ISO3
COUNTRY_NAME_TO_ISO3 = {}
for k, v in (_country_name_to_iso3_raw or {}).items():
    if isinstance(k, str) and isinstance(v, str):
        COUNTRY_NAME_TO_ISO3[_norm_country(k)] = v.strip().upper()

def resolve_user_input(raw: str):
    """
    Возвращает (ccy_code | None, country_iso3 | None).

    Правила:
    - если введена валюта/её алиас → (CCY, None)
    - если введена страна/её алиас (в т.ч. 4 буквы по-русски из json) → (валюта страны если известна, ISO3)
    - если распознаны оба (редко) → приоритет у явной валюты ввода
    """
    text_ccy = _norm_ccy(raw)
    text_cty = _norm_country(raw)

    # 1) валюта по алиасам
    ccy = None
    if re.fullmatch(r"[A-Z]{3}", text_ccy):
        ccy = text_ccy
    else:
        ccy = ALIAS_TO_CCY.get(text_ccy)

    # 2) страна по названиям/алиасам
    iso3 = COUNTRY_NAME_TO_ISO3.get(text_cty)

    # 3) если есть ISO3 и валюта не распознана напрямую — попробуем подтянуть по ISO3
    if iso3 and not ccy:
        ccy = ISO3_TO_CCY.get(iso3)

    return ccy, iso3

# опционально — простые геттеры, если где-то в коде пригодятся
def iso3_from_country_name(name: str):
    return COUNTRY_NAME_TO_ISO3.get(_norm_country(name))

def to_ccy_code(user_input: str):
    key = _norm_ccy(user_input)
    if re.fullmatch(r"[A-Z]{3}", key):
        return key
    return ALIAS_TO_CCY.get(key)