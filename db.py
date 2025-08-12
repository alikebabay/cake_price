#переключатель баз данных для фаерстор

import os
backend = os.getenv("DB_BACKEND") or ("firestore" if os.getenv("GOOGLE_CLOUD_PROJECT") else "sqlite")
if backend == "firestore":
    from db_firestore import *
else:
    from cake_database import *   # текущий модуль с SQLite
print(f"[db] backend = {backend}")