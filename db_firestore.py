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

def _fmt_ts(ts) -> str:
    # ts может быть None или datetime (UTC). Вернём строку как в SQLite.
    if ts is None:
        ts = datetime.now(timezone.utc)
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts.strftime("%Y-%m-%d %H:%M:%S")

def get_cached_rate(title: str):
    """Возвращает (rate, ts) как и SQLite; None если нет записи."""
    doc = _col().document(title.strip().upper()).get()
    if not doc.exists:
        return None
    data = doc.to_dict() or {}
    rate = float(data["rate"])
    ts = data.get("ts")
    return float(data["rate"]), data.get("ts")   # ts может быть None на самом первом чтении
