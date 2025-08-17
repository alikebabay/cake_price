from db import get_cached_rate, cache_rate, is_rate_cached
from calculator import convert_kzt
from datetime import datetime, timedelta
from config import CAKE_PRICE_KZT

MAX_AGE = timedelta(hours=24)

async def serve_cached_and_update(update, title: str):
    title = (title or "").strip().upper()
    # KZT — константа, без БД/сети
    if title == "KZT":
        await update.message.reply_text(
            f"Казахский торт стоит {CAKE_PRICE_KZT:,.2f} KZT"
        )
        return

    # 1) Проверяем кэш (материализованная цена торта в CCY)
    cached = get_cached_rate(title)  # ('USD', amount, 'YYYY-MM-DD HH:MM:SS') или None
    if cached:
        c, amount, ts = cached
        await update.message.reply_text(
                f"Кэш • 600000 KZT = {float(amount):,.2f} {c} (обновлено: {ts})"
            )
        return

    # 2) Кэша нет — считаем через API, сохраняем и отдаём
    new_amount = convert_kzt(title)  # 600k берётся из конфига внутри твоего кода
    if new_amount is not None:
        try:
            clean_amount = float(str(new_amount).replace(",", "").strip())
        except (ValueError, TypeError):
            await update.message.reply_text("❌ Ошибка: неверный формат курса.")
            return

        cache_rate(title, clean_amount)  # заодно обновит timestamp
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await update.message.reply_text(
            f"Создал • 600000 KZT = {clean_amount:,.2f} {title} (обновлено: {now_str})".replace(",", " ")
        )
        return

    # 3) Ни кэша, ни API
    await update.message.reply_text("⚠️ Сервис недоступен, кэша нет.")


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