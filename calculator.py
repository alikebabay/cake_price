import requests
from typing import Optional
from config import CAKE_PRICE_KZT

_API = "https://open.er-api.com/v6/latest/KZT"

def convert_kzt(title: str, amount_kzt: float | None = None) -> Optional[float]:
    """Возвращает материализованную цену 1 торта в валюте CCY.
    Если amount_kzt не передан — используем CAKE_PRICE_KZT из конфига."""

    ccy = (title or "").strip().upper()

    try:
        data = requests.get(_API, timeout=5).json()
        rate = data.get("rates", {}).get(ccy)
        if rate is None:
            return None
        base = CAKE_PRICE_KZT if amount_kzt is None else float(amount_kzt)
        return float(base) * float(rate)
    except Exception:
        return None

#тест
if __name__ == "__main__":
    while True:
        b = input("Узнать цену казахского торта. Введите название валюты (или exit для выхода): ").upper()
        if b == "EXIT":
            break
        # пример без прокси
        value = convert_kzt(600_000, b)
        if value is not None:
            print(f"600000 KZT = {value:,.2f} {b}")
        else:
            print("Валюта не найдена.")