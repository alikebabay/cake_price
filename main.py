#импорты
import logging
from typing import Final
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler)
import os
from config import TOKEN, BOT_USERNAME, assert_required
from rate_dispatcher import serve_cached_and_update
from cake_dictionary import (
    POPULAR_CURRENCIES, ALIAS_TO_CODE, _norm, _try_iso_code, CANCEL_ALIASES,
    currency_to_iso3,
)
from db import get_wage_doc, upsert_wage_doc  # ← просто чтобы было видно зависимость (использует диспетчер)


PORT = int(os.getenv("PORT", "8080"))                  # Cloud Run даст $PORT
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")   # сюда вставим URL сервиса после деплоя
WEBHOOK_PATH = "/tgwebhook"                            # конечная точка вебхука


# Включим ведение журнала
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

#состояния - глубина меню
MENU = 1

# 👉 общий резолвер: алиас/название/ISO → код валюты
def _resolve_code(text: str) -> str | None:
    key = _norm(text or "")
    return ALIAS_TO_CODE.get(key) or _try_iso_code(key)

#управление ботом
#команда старт
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton(code)] for code in sorted(POPULAR_CURRENCIES)]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Узнать цену казахского торта. Выберите популярную валюту или введите первые 4 буквы названия страны. Например, амер",
        reply_markup=reply_markup
    )
    return MENU





# ISO-коды вне диалога (раньше тут было просто .upper())
async def iso_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()
    code = _resolve_code(raw)
    if not code:
        await update.message.reply_text(
            "Не распознал валюту. Пришлите 3-буквенный ISO-код (например: EUR, GBP) "
            "или начните вводить первые 4 буквы названия страны."
        )
        return
    iso3 = currency_to_iso3(code)
    await serve_cached_and_update(update, code, country_iso3=iso3)
    return
# выбор валюты (оставляем ту же логику, но используем общий резолвер)
async def choose_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()

    if _norm(raw) in CANCEL_ALIASES:
        return await cancel(update, context)

    code = _resolve_code(raw)
    if code:
        iso3 = currency_to_iso3(code)
        await serve_cached_and_update(update, code, country_iso3=iso3)
        return MENU

    await update.message.reply_text(
        "Не распознал валюту. Популярные — на клавиатуре. "
        "Для остальных пришлите 3-буквенный ISO-код (например: EUR, GBP, TRY) "
        "или начните вводить первые 4 буквы названия страны."
    )
    return MENU

# Обработка /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Диалог завершён. Нажмите /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
#другие команды
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напишите валюту текстом (USD, рубль, юань) или используйте /start.")

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Это стандартный запрос")

#использование бота в чатах
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text or ""

    # В группах — реагируем только на упоминание бота
    if message_type in {"group", "supergroup"}:
        if not BOT_USERNAME or BOT_USERNAME not in text:
            return
        # вырезаем @bot из текста
        text = text.replace(BOT_USERNAME, "").strip()

    key = _norm(text)

    # Выходные слова
    if key in CANCEL_ALIASES:
        await update.message.reply_text("Диалог завершён. Нажмите /start, чтобы начать заново.")
        return

    # Валюта?
    code = ALIAS_TO_CODE.get(key) or _try_iso_code(key)
    if code:
        await serve_cached_and_update(update, code)
        return

    # Мягкая подсказка
    await update.message.reply_text(
        "Не распознал валюту. Популярные — на клавиатуре. "
        "Для остальных пришлите ISO-код: EUR, GBP, TRY и т.п."
    )

#обработка ошибок
async def error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Update %r caused error: %s", update, context.error)

#запуск бота
def main():
    if not TOKEN:
        print("FATAL: TELEGRAM_TOKEN is not set", flush=True)
        raise SystemExit(1)

    print(f"Бот запускается... @{BOT_USERNAME}" if BOT_USERNAME else "Бот запускается...", flush=True)

    application = Application.builder().token(TOKEN).concurrent_updates(False).build()

# Хендлер диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_currency)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        )
    application.add_handler(conv_handler) # group=0 по умолчанию
    # 2) отдельный хэндлер для ISO-кодов (ровно 3 латинские буквы)
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^[A-Za-z]{3}$") & ~filters.COMMAND,
            iso_handler
        )
    )

# Другие команды
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("custom", custom_command))

# Ответы на текстовые сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^[A-Za-z]{3}$"), handle_message), group=1)

# Обработка ошибок
    application.add_error_handler(error)
    # application.add_handler(...)

    if PUBLIC_URL:
        # Cloud Run: слушаем HTTP и выставляем вебхук
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH.strip("/"),
            webhook_url=f"{PUBLIC_URL}{WEBHOOK_PATH}",
            drop_pending_updates=True,
        )
    else:
        # локальная разработка: обычный polling
        application.run_polling(drop_pending_updates=True)



if __name__ == "__main__":
    main()


