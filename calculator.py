import requests, re


def convert_kzt(amount_kzt: float, title: str) -> float | None:
    """Возвращает пересчитанную сумму в валюте currency_code или None, если не найдено."""

    r = requests.get(
        'https://open.er-api.com/v6/latest/KZT',

    ).json()['rates'].get(title.upper())
    if r:
        return amount_kzt * r
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