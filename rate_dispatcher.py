from db import get_cached_rate, cache_rate, is_rate_cached, get_wage_doc, upsert_wage_doc
from calculator import convert_kzt, compute_cake_salary, _get_usd_kzt_rate
from datetime import datetime, timedelta
from config import CAKE_PRICE_KZT

MAX_AGE = timedelta(hours=24)

async def serve_cached_and_update(
    update,
    title: str,
    *,
    country_iso3: str | None = None,  # ISO3 домашней страны валюты (передаст мейн)
):
    title = (title or "").strip().upper()

    # KZT — константа, без БД/сети
    if title == "KZT":
        await update.message.reply_text(
            f"Казахский торт стоит {CAKE_PRICE_KZT:,.2f} KZT"
        )
        return

    # 1) Пробуем кэш (никакого TTL тут нет)
    cached = get_cached_rate(title)  # ('USD', amount, 'YYYY-MM-DD HH:MM:SS') или None
    if cached:
        c, amount, ts = cached
        msg = f"Кэш • 600000 KZT = {float(amount):,.2f} {c} (обновлено: {ts})"
    else:
        # 2) Кэша нет — считаем через API, сохраняем и готовим ответ
        new_amount = convert_kzt(title)  # 600k берётся из конфига внутри твоего кода
        if new_amount is None:
            await update.message.reply_text("⚠️ Сервис недоступен, кэша нет.")
            return
        try:
            clean_amount = float(str(new_amount).replace(",", "").strip())
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Ошибка: неверный формат курса.")
            return

        cache_rate(title, clean_amount)  # обновит timestamp
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"Создал • 600000 KZT = {clean_amount:,.2f} {title} (обновлено: {now_str})"

    # 3) Опциональный аппенд: «зарплата в тортах» по домашней стране валюты
    #    (используем Firestore-коллекцию avg_wages_unece)
    if country_iso3:
        doc = get_wage_doc(country_iso3)  # dict|None
        if doc:
            salary_usd = doc.get("salary_usd", doc.get("value"))
            if salary_usd is not None:
                # пробуем достать цену торта в USD из кэша
                usd_cached = get_cached_rate("USD")
                if usd_cached:
                    _, usd_price, _ = usd_cached


                else:

                    val = convert_kzt("USD")  # 600000 KZT в USD

                    price_usd = float(val) if val is not None else None

                    if price_usd is not None:
                        cache_rate("USD", price_usd)

                if price_usd:
                    # курс KZT за 1 USD = (600000 KZT) / (600000 KZT в USD)
                    kzt_per_usd = CAKE_PRICE_KZT / float(price_usd)

                    # подготовим «красивую» метку времени (и для апдейта, и для печати)
                    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

                    # вызываем новый калькулятор
                    calc = compute_cake_salary(float(salary_usd), kzt_per_usd=kzt_per_usd)

                    cake_salary = calc["cake_salary"]
                    salary_kzt = calc["salary_kzt"]
                    now_str = calc["updated_at"]

                    # апсертим обратно в wages
                    try:
                        upsert_wage_doc(country_iso3, {
                            "cake_salary": cake_salary,
                            "salary_kzt": salary_kzt,
                            "updated_at": now_str,
                        })
                    except Exception:
                        pass

                    # оформление ответа
                    country_name = doc.get("country", country_iso3)
                    src = calc.get("source", {})
                    src_name = src.get("name", "UNECE")
                    src_year = src.get("year", 2024)
                    src_url = src.get("url", "")

                    upd_display = _fmt_ts(doc.get("updated_at") or doc.get("ingested_at") or now_str)

                    msg += (
                        f"\n\nСредняя зарплата в {country_name}: {salary_kzt:,.0f} KZT"
                        f"\nИсточник: {src_name} ({src_year}), ссылка: {src_url} ({upd_display})"
                        f"\nЭто ≈ {cake_salary:,.2f} тортов (600 000 KZT за торт)"
                    )

    await update.message.reply_text(msg.replace(",", " "))

#форматтер времени
def _fmt_ts(v):
    try:
        from datetime import datetime
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        return "" if v is None else str(v)
    except Exception:
        return ""

#тест
import asyncio

# Фейковый update с подменой reply_text
class FakeMessage:
    async def reply_text(self, text):
        print(f"[BOT]: {text}")

class FakeUpdate:
    message = FakeMessage()

# Запускаем тест
if __name__ == "__main__":
    # Подставь код валюты, например USD
    asyncio.run(serve_cached_and_update(FakeUpdate(), "rub"))