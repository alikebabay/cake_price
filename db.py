#переключатель баз данных для фаерстор
# db.py
import os

backend = os.getenv("DB_BACKEND") or ("firestore" if os.getenv("GOOGLE_CLOUD_PROJECT") else "sqlite")

if backend == "firestore":
    from db_firestore import (
        is_rate_cached,
        cache_rate,
        get_cached_rate,
        get_wage_doc,
        upsert_wage_doc,
    )
else:
    from cake_database import (
        is_rate_cached,
        cache_rate,
        get_cached_rate,
    )


    # ← заглушки, чтобы импорт в rate_dispatcher не падал
    def get_wage_doc(iso3: str):
        return None


    def upsert_wage_doc(iso3: str, patch: dict):
        return None

__all__ = [
    "is_rate_cached",
    "cache_rate",
    "get_cached_rate",
]

# Эти есть только в firestore-бэкенде
if backend == "firestore":
    __all__ += [
        "get_wage_doc",
        "upsert_wage_doc",
    ]