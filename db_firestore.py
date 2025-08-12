# db_firestore.py
import os
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
    _col().document(title.strip().upper()).set({
        "rate": float(rate),
        "ts": firestore.SERVER_TIMESTAMP,   # время сервера
    })

def get_cached_rate(title: str):
    """Возвращает (rate, ts) как и SQLite; None если нет записи."""
    doc = _col().document(title.strip().upper()).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    return float(data["rate"]), data.get("ts")   # ts может быть None на самом первом чтении

# на всякий случай оставим удобный шорткат
def get_rate(title: str):
    res = get_cached_rate(title)
    return None if res is None else res[0]