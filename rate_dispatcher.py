from db import get_cached_rate, cache_rate, is_rate_cached, get_wage_doc, upsert_wage_doc
from calculator import convert_kzt, compute_cake_salary, _get_usd_kzt_rate
from datetime import datetime, timedelta
from config import CAKE_PRICE_KZT

MAX_AGE = timedelta(hours=24)

async def serve_cached_and_update(update, title: str, *, country_iso3: str | None = None):
    title = (title or "").strip().upper()

    if title == "KZT":
        await update.message.reply_text(f"Казахский торт стоит {CAKE_PRICE_KZT:,.2f} KZT")
        return

    cached = get_cached_rate(title)
    if cached:
        code, amount, ts = cached
    else:
        new_amount = convert_kzt(title)
        if new_amount is None:
            await update.message.reply_text("⚠️ Сервис недоступен, кэша нет.")
            return
        try:
            amount = float(str(new_amount).replace(",", "").strip())
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Ошибка: неверный формат курса.")
            return
        cache_rate(title, amount)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        code = title

    msg = f"{'Кэш' if cached else 'Создал'} • 600000 KZT = {amount:,.2f} {code} (обновлено: {ts})"

    if country_iso3:
        # USD обязателен — иначе ничего не отправляем
        usd_cached = get_cached_rate("USD")
        if usd_cached:
            _, price_usd, _ = usd_cached
        else:
            val = convert_kzt("USD")
            if val is not None:
                price_usd = float(val)
                cache_rate("USD", price_usd)
            else:
                await update.message.reply_text("⚠️ Не удалось получить курс USD, расчёт зарплаты невозможен.")
                return

        extra = append_salary(country_iso3, price_usd)
        if extra:
            msg += "\n\n" + extra
        else:
            await update.message.reply_text("⚠️ Зарплата не найдена.")
            return

    await update.message.reply_text(msg.replace(",", " "))

def append_salary(country_iso3: str, price_usd: float) -> str | None:
    doc = get_wage_doc(country_iso3)
    if not doc:
        return None

    salary_usd = doc.get("salary_usd", doc.get("value"))
    if salary_usd is None:
        return None

    kzt_per_usd = CAKE_PRICE_KZT / price_usd
    calc = compute_cake_salary(float(salary_usd), kzt_per_usd=kzt_per_usd)

    cake_salary = calc["cake_salary"]
    salary_kzt = calc["salary_kzt"]
    now_str = calc["updated_at"]

    try:
        upsert_wage_doc(country_iso3, {
            "cake_salary": cake_salary,
            "salary_kzt": salary_kzt,
            "updated_at": now_str,
        })
    except Exception:
        pass

    country_name = doc.get("country", country_iso3)
    src = calc.get("source", {})
    src_name = src.get("name", "UNECE")
    src_year = src.get("year", 2024)
    src_url = src.get("url", "")
    upd_display = _fmt_ts(doc.get("updated_at") or doc.get("ingested_at") or now_str)

    return (
        f"\n\nСредняя зарплата в {country_name}: {salary_kzt:,.0f} KZT"
        f"\nИсточник: {src_name} ({src_year}), ссылка: {src_url} ({upd_display})"
        f"\nЭто ≈ {cake_salary:,.2f} тортов (600 000 KZT за торт)"
    )


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