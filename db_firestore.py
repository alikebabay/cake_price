# db_firestore.py
import os
from datetime import datetime, timezone
from google.cloud import firestore

_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
_db = None

def _get_db():
    global _db
    if _db is None:
        _db = firestore.Client(project=_PROJECT)
    return _db

def _col():
    return _get_db().collection("exchange_rates")

def is_rate_cached(title: str) -> bool:
    return _col().document(title.strip().upper()).get().exists

def cache_rate(title: str, rate: float):
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    _col().document(title.strip().upper()).set({
        "rate": float(rate),
        "ts": expires_at,                 # время истечения
        "updated_at": firestore.SERVER_TIMESTAMP  # для отладки   # время сервера
    })

def _ts_to_str(ts) -> str:
    # Firestore может вернуть None или aware-datetime
    if ts is None:
        ts = datetime.now(timezone.utc)
    if getattr(ts, "tzinfo", None):
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def get_cached_rate(title: str):
    """
    Возвращает (TITLE, RATE, TS_STR) — полностью как в SQLite.
    """
    t = title.strip().upper()
    doc = _col().document(t).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    rate = float(data["rate"])
    ts_str = _ts_to_str(data.get("ts"))
    return t, rate, ts_str
