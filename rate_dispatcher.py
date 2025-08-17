from db import get_cached_rate, cache_rate, is_rate_cached, get_wage_doc, upsert_wage_doc
from calculator import convert_kzt
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
            # В UNECE поле может называться 'value' (USD)
            salary_usd = doc.get("salary_usd", doc.get("value"))
            if salary_usd is not None:
                # Нужна цена торта в USD (600k KZT -> USD), берём тем же кэшем
                usd_cached = get_cached_rate("USD")
                if usd_cached:
                    _, usd_price, _ = usd_cached
                    price_usd = float(usd_price)
                else:
                    na = convert_kzt("USD")
                    price_usd = float(str(na).replace(",", "").strip()) if na is not None else None
                    if price_usd is not None:
                        cache_rate("USD", price_usd)

                if price_usd:
                    cake_salary = float(salary_usd) / float(price_usd)
                    salary_kzt = cake_salary * float(CAKE_PRICE_KZT)

                    # кэшируем в том же документе UNECE
                    try:
                        upsert_wage_doc(country_iso3, {
                            "cake_salary": cake_salary,
                            "salary_kzt": salary_kzt,
                            "updated_at": datetime.utcnow().isoformat()
                        })
                    except Exception:
                        # не валим ответ пользователю, если апдейт не удался
                        pass

                    country_name = doc.get("country", country_iso3)
                    src = doc.get("source") or {}
                    upd = doc.get("updated_at")

                    msg += (
                        f"\n\nСредняя зарплата в {country_name}: {salary_kzt:,.0f} KZT"
                        f"\nЭто ≈ {cake_salary:,.2f} тортов (600 000 KZT за торт)"
                    )
                    if src or upd:
                        src_name = src.get("name", "UNECE")
                        src_year = src.get("year", 2024)
                        src_url  = src.get("url", "")
                        msg += f"\nИсточник: {src_name} ({src_year}), {src_url} ({upd})"

    await update.message.reply_text(msg)


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