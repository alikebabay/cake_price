#импорты
import logging
from typing import Final
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler)
import os
from config import TOKEN, BOT_USERNAME, assert_required
from rate_dispatcher import serve_cached_and_update
from cake_dictionary import resolve_user_input
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


POPULAR_CURRENCIES = "USD, UAH, BYN, RUB, CNY, UZS, KGS, AMD, GBP"

#нормализатор
def _norm_cmd(s: str) -> str:
    return (s or "").strip().upper().replace("Ё", "Е")
CANCEL_ALIASES = {"EXIT", "ВЫХОД", "ОТМЕНА", "CANCEL"}



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
    ccy_code, country_iso3 = resolve_user_input(raw)  # ('USD','USA') | (None,'KAZ') | (None,None)

    if not ccy_code and not country_iso3:
        await update.message.reply_text(
            "Не распознал ввод. Введите валюту ($, USD, тенге) или страну (США, Kazakhstan)."
        )
        return

    await serve_cached_and_update(update, ccy_code=ccy_code, country_iso3=country_iso3)

# выбор валюты (оставляем ту же логику, но используем общий резолвер)
async def choose_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()

    if _norm_cmd(raw) in CANCEL_ALIASES:
        return await cancel(update, context)

    ccy_code, country_iso3 = resolve_user_input(raw)

    if ccy_code or country_iso3:
        await serve_cached_and_update(update, ccy_code=ccy_code, country_iso3=country_iso3)
        return MENU

    await update.message.reply_text(
        "Не распознал ввод. Популярные — на клавиатуре. "
        "Можно прислать ISO-код (EUR, GBP, TRY) или название страны (например: США, Kazakhstan)."
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
    text: str = (update.message.text or "").strip()

    # В группах — реагируем только на упоминание бота
    if message_type in {"group", "supergroup"}:
        if not BOT_USERNAME or BOT_USERNAME not in text:
            return
        text = text.replace(BOT_USERNAME, "").strip()

    # Служебные выходные слова
    if _norm_cmd(text) in CANCEL_ALIASES:
        await update.message.reply_text("Диалог завершён. Нажмите /start, чтобы начать заново.")
        return

    # Универсальный резолвер: валюта/страна → (ccy_code, iso3)
    ccy_code, country_iso3 = resolve_user_input(text)

    if ccy_code or country_iso3:
        # Лог по желанию
        # logging.debug("Resolved input: ccy=%s iso3=%s", ccy_code, country_iso3)
        await serve_cached_and_update(update, ccy_code=ccy_code, country_iso3=country_iso3)
        return

    # Подсказка
    await update.message.reply_text(
        "Не распознал ввод. Популярные валюты — на клавиатуре. "
        "Или пришлите ISO-код (EUR, GBP, TRY) или название страны (США, Kazakhstan)."
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

    # Диалог выбора (внутри состояния MENU используем choose_currency → resolve_user_input)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_currency)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler, group=0)

    # Остальные команды (если есть)
    application.add_handler(CommandHandler("help", help_command), group=0)
    application.add_handler(CommandHandler("custom", custom_command), group=0)

    # Общий обработчик для чатов/групп, когда мы НЕ в состоянии диалога
    # (использует resolve_user_input внутри handle_message)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
        group=1,   # важно: после conv_handler
    )

    application.run_polling(allowed_updates=Update.ALL_TYPES)



if __name__ == "__main__":
    main()


