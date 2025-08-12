from db import get_cached_rate, cache_rate, is_rate_cached
from calculator import convert_kzt
from datetime import datetime, timedelta

MAX_AGE = timedelta(hours=24)

async def serve_cached_and_update(update, title: str):
    title = title.strip().upper()

    # 1. Проверяем кэш
    cached = get_cached_rate(title)  # ('USD', 1282.05, '2025-08-10 15:42:00') или None
    if cached:
        c, rate, ts = cached
        # ts в формате "YYYY-MM-DD HH:MM:SS"
        age = datetime.now() - datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

        if age <= MAX_AGE:
            await update.message.reply_text(
                f"Кэш • 600000 KZT = {float(rate):,.2f} {c} (обновлено: {ts})"
            )
            return


        # Старше 24 ч — тянем новый курс
        new_rate = convert_kzt(600_000, title)
        if new_rate is not None:
            try:
                clean_rate = float(str(new_rate).replace(",", "").strip())
            except (ValueError, TypeError):
                await update.message.reply_text("❌ Ошибка: неверный формат курса.")
                return

            cache_rate(title, clean_rate)  # обновит и timestamp
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await update.message.reply_text(
                f"Обновил • 600000 KZT = {clean_rate:,.2f} {title} (обновлено: {now_str})"
            )
            return
        else:
            # API недоступно — показываем устаревший кэш
            await update.message.reply_text(
                f"⚠️ Сервис недоступен. Показываю кэш {float(rate):,.2f} {c} (обновлено: {ts})"
            )
            return

    else:
        # 3) Кэша нет — тянем из API, сохраняем и отдаём
        new_rate = convert_kzt(600_000, title)
        if new_rate is not None:
            try:
                clean_rate = float(str(new_rate).replace(",", "").strip())
            except (ValueError, TypeError):
                await update.message.reply_text("❌ Ошибка: неверный формат курса.")
                return

            cache_rate(title, clean_rate)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await update.message.reply_text(
                f"Создал • 600000 KZT = {clean_rate:,.2f} {title} (обновлено: {now_str})"
            )
            return
        else:
            await update.message.reply_text("⚠️ Сервис недоступен, кэша нет.")
            return


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