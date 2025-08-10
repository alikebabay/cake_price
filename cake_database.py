import sqlite3
from datetime import datetime
import os
from config import DB_PATH

TS_FMT = "%Y-%m-%d %H:%M:%S"

#проверка индекса
def _ensure_schema(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL UNIQUE,
        rate  FLOAT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_exchange_rates_title ON exchange_rates(title)")

def is_rate_cached(title: str) -> bool:
    title = str(title).strip().upper()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    _ensure_schema(cur)  # ← ДОБАВЬ
    cur.execute("SELECT 1 FROM exchange_rates WHERE title = ? LIMIT 1", (title,))
    ok = cur.fetchone() is not None
    con.close()
    return ok

def cache_rate(title: str, rate: float):
    title = str(title).strip().upper()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exchange_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL UNIQUE,
        rate  FLOAT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_exchange_rates_title ON exchange_rates(title)")

    # если такая валюта уже есть — просто ничего не делаем
    cur.execute("""
                INSERT INTO exchange_rates (title, rate)
                VALUES (?, ?) ON CONFLICT(title) DO
                UPDATE SET
                    rate = excluded.rate,
                    timestamp = CURRENT_TIMESTAMP
                """, (title, rate))
    #добавляем запись и закрываем коннекшен
    con.commit()
    con.close()
def get_cached_rate(title: str) -> tuple[str, float, str] | None:
    """
    Возвращает последнюю запись для указанной валюты.
    Формат: (title, rate, timestamp) или None, если нет данных.
    """
    title = str(title).strip().upper()
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    _ensure_schema(cur)  # проверка индекса
    cur.execute("""
        SELECT title, rate, timestamp
        FROM exchange_rates
        WHERE title = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (title.upper(),))
    row = cur.fetchone()
    con.close()
    return row

# 🧪 Тест — будет работать только если запустить файл вручную
if __name__ == "__main__":
    print("🧪 Тестовая вставка и вывод:")

    # Тест: добавим одну запись
    cache_rate("uah", 45929.12)

    # Тест: прочитаем все записи
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT * FROM exchange_rates")
    results = cur.fetchall()

    print("📦 Данные в базе:")
    for row in results:
        print(row)

    con.close()