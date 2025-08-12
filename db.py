#переключатель баз данных для фаерстор

import os
backend = os.getenv("DB_BACKEND") or ("firestore" if os.getenv("GOOGLE_CLOUD_PROJECT") else "sqlite")
if backend == "firestore":
    from db_firestore import is_rate_cached as _is_rate_cached, cache_rate as _cache_rate, get_cached_rate as _raw_get_cached_rate
else:
    from cake_database import is_rate_cached as _is_rate_cached, cache_rate as _cache_rate, get_cached_rate as _raw_get_cached_rate

def is_rate_cached(title: str) -> bool:
    return _is_rate_cached(title)

def cache_rate(title: str, rate: float):
    return _cache_rate(title, rate)

def get_cached_rate(title: str):
    """
    Нормализованный контракт: всегда (rate, ts, source).
    Поддержим любые старые варианты: float, (rate,), (rate, ts), (rate, ts, src).
    """
    res = _raw_get_cached_rate(title)
    if res is None:
        return None
    # уже кортеж из 3
    if isinstance(res, tuple) and len(res) == 3:
        return res
    # кортеж из 2
    if isinstance(res, tuple) and len(res) == 2:
        rate, ts = res
        return float(rate), ts, backend
    # одиночное значение
    try:
        rate = float(res)
        return rate, None, backend
    except Exception:
        # на всякий: вернуть как есть, но допилить source
        return res, None, backend