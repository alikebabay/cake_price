# db_firestore.py
import os
from datetime import datetime, timezone, timedelta
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
    try:
        if ts is None:
            return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(ts, datetime):
            return ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        # на случай SERVER_TIMESTAMP-сентинела или чего-то другого
        return str(ts)
    except Exception as e:
        import logging
        logging.exception("Bad timestamp value: %r", ts)
        return "1970-01-01 00:00:00"

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
