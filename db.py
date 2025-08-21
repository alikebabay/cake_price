# db.py — только Firestore

from db_firestore import (
    is_rate_cached,
    cache_rate,
    get_cached_rate,
    get_wage_doc,
    upsert_wage_doc,
    _wages_col,
)

__all__ = [
    "is_rate_cached",
    "cache_rate",
    "get_cached_rate",
    "get_wage_doc",
    "upsert_wage_doc",
    "_wages_col",
]