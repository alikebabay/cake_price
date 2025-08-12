#переключатель баз данных для фаерстор
# db.py
import os

backend = os.getenv("DB_BACKEND") or ("firestore" if os.getenv("GOOGLE_CLOUD_PROJECT") else "sqlite")

if backend == "firestore":
    from db_firestore import is_rate_cached, cache_rate, get_cached_rate
else:
    from cake_database import is_rate_cached, cache_rate, get_cached_rate