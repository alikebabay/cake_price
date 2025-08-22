import requests
from typing import Optional
from datetime import datetime, timezone
from config import CAKE_PRICE_KZT, UNECE_YEAR

_API = "https://open.er-api.com/v6/latest/KZT"

class FXError(Exception): ...
class NoWageError(Exception): ...


def _get_usd_kzt_rate() -> float:
    """Берём курс USD/KZT из внешнего API."""
    r = requests.get(_API, timeout=10)
    if r.status_code != 200:
        raise FXError(f"FX API error: {r.status_code}")
    data = r.json()
    # API: base=KZT, rates.USD -> сколько USD за 1 KZT
    usd_per_kzt = data["rates"]["USD"]
    # Нам нужен KZT за 1 USD, поэтому берём обратное
    kzt_per_usd = 1 / usd_per_kzt
    return kzt_per_usd


def compute_cake_salary(salary_usd: float, *, kzt_per_usd: float) -> dict:
    """
    Чистая функция: считает зарплату в KZT и «в тортах»,
    если на входе дана зарплата (в USD) и курс (KZT за 1 USD).
    """
    if salary_usd is None:
        raise NoWageError("No UNECE wage provided")

    cake_price_usd = CAKE_PRICE_KZT / float(kzt_per_usd)
    cake_salary = float(salary_usd) / cake_price_usd
    salary_kzt = float(salary_usd) * float(kzt_per_usd)

    return {
        "salary_kzt": salary_kzt,
        "cake_salary": cake_salary,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "fx": {
            "pair": "USD/KZT",
            "rate": float(kzt_per_usd),
            "api": _API,  # справочно
        },
    }

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