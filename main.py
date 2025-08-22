#импорты
import logging
from typing import Final
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler)
import os
from config import TOKEN, BOT_USERNAME, assert_required
from rate_dispatcher import serve_cached_and_update
from cake_dictionary import resolve_user_input
import re

PORT = int(os.getenv("PORT", "8080"))                  # Cloud Run даст $PORT
PUBLIC_URL = os.getenv("PUBLIC_URL", "").rstrip("/")   # сюда вставим URL сервиса после деплоя
WEBHOOK_PATH = "/tgwebhook"                            # конечная точка вебхука


# Включим ведение журнала
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


POPULAR_CURRENCIES: Final[tuple[str, ...]] = (
    "USD", "UAH", "BYN", "RUB", "CNY", "UZS", "KGS", "AMD", "GBP"
)
#клавиатура пользователя
def build_currency_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(code)] for code in sorted(POPULAR_CURRENCIES)]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


#нормализатор
def _norm_cmd(s: str) -> str:
    return (s or "").strip().upper().replace("Ё", "Е")
CANCEL_ALIASES = {"EXIT", "ВЫХОД", "ОТМЕНА", "CANCEL"}

#санитайзер для удаления united states
def _sanitize_pair(ccy_code: str | None, country_iso3: str | None) -> tuple[str | None, str | None]:
    ccy = (ccy_code or "").strip().upper()
    iso3 = (country_iso3 or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", ccy):
        ccy = None
    if not re.fullmatch(r"[A-Z]{3}", iso3):
        iso3 = None
    return ccy, iso3

#управление ботом
#команда старт
async def start_command(update, context):
    await update.message.reply_text(
        "Узнать цену казахского торта.\n"
        "Выберите популярную валюту или введите первые 4-5 букв названия страны (напр., «амер», «австри»).",
        reply_markup=build_currency_keyboard(),
    )


#обработчик текста общий
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return

    text = (msg.text or "").strip()

    # в группах реагируем только на упоминание бота
    if msg.chat.type in {"group", "supergroup"}:
        if not BOT_USERNAME or BOT_USERNAME not in text:
            return
        text = text.replace(BOT_USERNAME, "").strip()

    # служебные слова выхода
    if _norm_cmd(text) in CANCEL_ALIASES:
        await cancel(update, context)
        return

    # ВСЕГДА: сначала резолвер → потом санитайзер → потом диспетчер
    ccy_code, country_iso3 = resolve_user_input(text)
    ccy_code, country_iso3 = _sanitize_pair(ccy_code, country_iso3)

    if ccy_code or country_iso3:
        await serve_cached_and_update(update, ccy_code=ccy_code, country_iso3=country_iso3)
        return

    await msg.reply_text(
        "Не распознал ввод. Популярные валюты — на клавиатуре (/start). "
        "Или пришлите ISO-код (EUR, GBP, TRY) или название страны (США, Kazakhstan)."
    )

# Обработка /cancel
async def cancel(update, context):
    await update.message.reply_text(
        "Диалог завершён. Нажмите /start, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove(),
    )

#другие команды
async def help_command(update, context):
    await update.message.reply_text(
        "Вдохновителем бота стала история с <a href='https://tengrinews.kz/story/istoriya-pro-tort-600-tyisyach-tenge-516358/'>неоплаченным тортом за 600 тысяч</a>.\n\n"
        "Нажмите /start для клавиатуры.",
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def custom_command(update, context):
    await update.message.reply_text("Это стандартный запрос.")


#обработка ошибок
async def error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Update %r caused error: %s", update, context.error)

#запуск бота
def main():
    if not TOKEN:
        print("FATAL: TELEGRAM_TOKEN is not set", flush=True)
        raise SystemExit(1)

    print(f"Бот запускается... @{BOT_USERNAME}" if BOT_USERNAME else "Бот запускается...", flush=True)

    app = Application.builder().token(TOKEN).concurrent_updates(False).build()

    # регистрируем из шага 8
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("custom", custom_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)
    if PUBLIC_URL:
        # Вебхук для продакшна (Cloud Run)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_path=WEBHOOK_PATH,
            webhook_url=f"{PUBLIC_URL}{WEBHOOK_PATH}",
        )
    else:
        # Polling для локальной разработки
        app.run_polling()


if __name__ == "__main__":
    main()


