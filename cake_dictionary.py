# cake_dictionary.py
from typing import Final, Optional, Tuple, Mapping
import json, re, unicodedata
from importlib.resources import files

# ── нормализация ──────────────────────────────────────────────────────────────
def _norm_ccy(s: str) -> str:
    # для валют: убираем пробелы/лишние знаки, оставляем буквы/цифры/символы валют
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    return re.sub(r"[^A-ZА-Я0-9$₽¥₼€£]", "", s)

def _norm_country(s: str) -> str:
    # для стран: сохраняем пробелы между словами
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    return re.sub(r"\s+", " ", s)

# ── загрузка данных ───────────────────────────────────────────────────────────
def _load_json(pkgfile: str) -> dict:
    return json.loads(files("cake_data").joinpath(pkgfile).read_text("utf-8"))

_ALIASES_RAW = _load_json("aliases.json")  # {"USD": ["USD","$","ДОЛЛАР",...]}
_CCY_TO_ISO3_RAW = _load_json("currency_to_iso3.json")  # {"USD":"USA", ...}
_COUNTRY_NAME_TO_ISO3_RAW = _load_json("country_name_to_iso3.json")  # {"UNITED STATES":"USA", ...}

# ── утилиты для очистки ───────────────────────────────────────────────────────
def _to_upper(s) -> str | None:
    if isinstance(s, str):
        s2 = s.strip().upper()
        return s2 or None
    return None

# ── построение мап (безопасно к мусору) ──────────────────────────────────────
# алиас валюты → ISO-код валюты
_alias_map: dict[str, str] = {}
for code, aliases in (_ALIASES_RAW or {}).items():
    code_u = _to_upper(code)
    if not code_u or not isinstance(aliases, list):
        continue
    for alias in aliases:
        alias_u = _to_upper(alias)
        if alias_u:
            _alias_map[alias_u] = code_u
    # код на самого себя
    _alias_map[code_u] = code_u

ALIAS_TO_CODE: Final[Mapping[str, str]] = _alias_map

# валюта → ISO3 страны
_CCY_TO_ISO3: dict[str, str] = {}
for k, v in (_CCY_TO_ISO3_RAW or {}).items():
    k_u, v_u = _to_upper(k), _to_upper(v)
    if k_u and v_u:
        _CCY_TO_ISO3[k_u] = v_u
_CCY_TO_ISO3 = _CCY_TO_ISO3  # keep as dict or wrap in Mapping if нужно
# при желании: _CCY_TO_ISO3: Final[Mapping[str, str]] = _CCY_TO_ISO3

# название страны → ISO3
COUNTRY_NAME_TO_ISO3: dict[str, str] = {}
def _norm_country(s: str) -> str:
    import unicodedata, re
    s = unicodedata.normalize("NFKC", (s or "")).strip().upper().replace("Ё", "Е")
    return re.sub(r"\s+", " ", s)

for k, v in (_COUNTRY_NAME_TO_ISO3_RAW or {}).items():
    k_u, v_u = _to_upper(k), _to_upper(v)
    if k_u and v_u:
        COUNTRY_NAME_TO_ISO3[_norm_country(k_u)] = v_u


# ── API ───────────────────────────────────────────────────────────────────────
def to_ccy_code(user_input: str) -> Optional[str]:
    """Любой ввод про валюту → ISO4217 (USD/EUR/...)."""
    key = _norm_ccy(user_input)
    if m := re.fullmatch(r"[A-Z]{3}", key):
        return key
    return ALIAS_TO_CODE.get(key)

def iso3_from_currency(ccy: str | None) -> Optional[str]:
    """Код валюты → ISO3 страны (USD→USA, KZT→KAZ...)."""
    return _CCY_TO_ISO3.get((ccy or "").strip().upper()) if ccy else None

def iso3_from_country_name(country_name: str) -> Optional[str]:
    """Название страны → ISO3 (UNITED STATES→USA)."""
    return COUNTRY_NAME_TO_ISO3.get(_norm_country(country_name))

def resolve_user_input(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Универсальный резолвер: из одного ввода получаем (валюта ISO4217, страна ISO3).
    Примеры:
      'амер' / '$' / 'usd'      → ('USD', 'USA')
      'United States' / 'США'   → ('USD', 'USA')  # при наличии в json
    """
    # 1) пробуем как валюту
    ccy = to_ccy_code(raw)
    if ccy:
        return ccy, iso3_from_currency(ccy)
    # 2) пробуем как страну
    iso3 = iso3_from_country_name(raw)
    if iso3:
        # опционально: если нужна «домашняя» валюта страны — добавь обратную мапу iso3->ccy
        return to_ccy_code("USD") if iso3 == "USA" else None, iso3
    return None, None