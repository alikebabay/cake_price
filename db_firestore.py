# db_firestore.py
import os
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from config import UNECE_YEAR, UNECE_UNIT
from cake_dictionary import COUNTRY_NAME_TO_ISO3  # NAME -> ISO3

USE_EMULATOR = bool(os.getenv("FIRESTORE_EMULATOR_HOST"))  # эмулятор используется только если переменная выставлена

_db = None


print(f"[Firestore] project={os.getenv('GOOGLE_CLOUD_PROJECT')} emulator={os.getenv('FIRESTORE_EMULATOR_HOST') or '-'}", flush=True)

def _get_db():
    global _db
    if _db is None:
        # Если нужно, можно явно пробросить project:
        _db = firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
        print(f"[Firestore] project={os.getenv('GOOGLE_CLOUD_PROJECT')} "
              f"emulator={os.getenv('FIRESTORE_EMULATOR_HOST') or '-'}", flush=True)
    return _db

def _col():
    return _get_db().collection("exchange_rates")

def _wages_col():
    return _get_db().collection("avg_wages_unece")

# ── добавляем обратную мапу ISO3 -> NAME (берём первый попавшийся нейм)
# если в COUNTRY_NAME_TO_ISO3 несколько неймов на один ISO3, выберем любой стабильный
ISO3_TO_COUNTRY_NAME: dict[str, str] = {}
for name, iso in COUNTRY_NAME_TO_ISO3.items():
    ISO3_TO_COUNTRY_NAME.setdefault(iso, name)

def _doc_id(key: str, year: int, unit: str) -> str:
    return f"{key.strip().upper()}_{year}_{unit.strip().upper()}"

def _doc_id_candidates_from_iso3(iso3: str, year: int, unit: str) -> list[str]:
    iso3 = (iso3 or "").strip().upper()
    ids = { _doc_id(iso3, year, unit) }
    # попробовать старый стиль: NAME_YYYY_UNIT
    name = ISO3_TO_COUNTRY_NAME.get(iso3)
    if name:
        ids.add(_doc_id(name, year, unit))
    return list(ids)

# ───────────────────────────────
# WAGES

def get_wage_doc(iso3: str, year: int = UNECE_YEAR, unit: str = UNECE_UNIT) -> dict | None:
    """Пробуем найти документ и по ISO3, и по NAME (для старой схемы ID)."""
    for doc_id in _doc_id_candidates_from_iso3(iso3, year, unit):
        snap = _wages_col().document(doc_id).get()
        if snap.exists:
            return snap.to_dict()
    return None

def upsert_wage_doc(iso3: str, patch: dict, year: int = UNECE_YEAR, unit: str = UNECE_UNIT) -> None:
    """
    Обновляем существующий документ, если он уже есть под ISO3_ID или NAME_ID.
    Если не нашли — создаём под СТАРЫМ стилем (NAME_YYYY_UNIT), чтобы не ломать твою базу.
    """
    iso3 = (iso3 or "").strip().upper()
    candidates = _doc_id_candidates_from_iso3(iso3, year, unit)

    # 1) если есть существующий — обновим его
    for doc_id in candidates:
        ref = _wages_col().document(doc_id)
        if ref.get().exists:
            if "updated_at" not in patch:
                patch = {**patch, "updated_at": firestore.SERVER_TIMESTAMP}
            # проставим iso3 внутри документа
            patch = {"iso3": iso3, **patch}
            ref.set(patch, merge=True)
            return

    # 2) иначе создаём НОВЫЙ документ в старом стиле (NAME_YYYY_UNIT)
    name = ISO3_TO_COUNTRY_NAME.get(iso3, iso3)  # если имени нет, упадём на ISO3
    doc_id = _doc_id(name, year, unit)
    if "updated_at" not in patch:
        patch = {**patch, "updated_at": firestore.SERVER_TIMESTAMP}
    patch = {"iso3": iso3, **patch}
    _wages_col().document(doc_id).set(patch, merge=True)

# ───────────────────────────────
# EXCHANGE RATES (без изменений)

def is_rate_cached(title: str) -> bool:
    return _col().document(title.strip().upper()).get().exists

def cache_rate(title: str, rate: float):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    _col().document(title.strip().upper()).set({
        "rate": float(rate),
        "ts": expires_at,
        "updated_at": firestore.SERVER_TIMESTAMP
    })

def _ts_to_str(ts) -> str:
    try:
        if ts is None:
            return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(ts, datetime):
            return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)
    except Exception:
        import logging
        logging.exception("Bad timestamp value: %r", ts)
        return "1970-01-01 00:00:00"

def get_cached_rate(title: str):
    t = title.strip().upper()
    doc = _col().document(t).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    rate = float(data["rate"])
    ts_str = _ts_to_str(data.get("ts"))
    return t, rate, ts_str