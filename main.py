#импорты
import logging
from typing import Final
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler)
import os
from config import TOKEN, BOT_USERNAME, assert_required
from rate_dispatcher import serve_cached_and_update




POPULAR_CURRENCIES = {"USD", "BYN", "UAH", "RUB", "KGS", "UZS", "CNY"}

# Включим ведение журнала
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


#состояния - глубина меню
MENU, DISTRICT_SELECTED = range(2)

#управление ботом
#команда старт
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("USD")],
        [KeyboardButton("BYN")],
        [KeyboardButton("UAH")],
        [KeyboardButton("RUB")],
        [KeyboardButton("KGS")],
        [KeyboardButton("UZS")],
        [KeyboardButton("CNY")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Узнать цену казахского торта. Введите название валюты (или exit для выхода):", reply_markup=reply_markup)
    return MENU
#выбор валюты
async def choose_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()

    if code in POPULAR_CURRENCIES:
        # тут больше не считаем сами — всё делает диспетчер (кэш/апи/сохранение/ответ)
        await serve_cached_and_update(update, code)
    else:
        await update.message.reply_text("Введите название валюты вручную или нажмите /start.")

    return MENU


# Обработка /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён.")
    return ConversationHandler.END

#другие команды
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Печатайте команды, чтобы получить помощь")

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Это стандартный запрос")

#использование бота в чатах
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == "group":
        if BOT_USERNAME in text:
            new_text: str = text.replace(BOT_USERNAME, "").strip()
            response: str = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)
    print("Bot", response)
    await update.message.reply_text(response)
# 🔽 Добавляем мягкую заглушку
def handle_response(text: str) -> str:
    return (
        "Я пока не понимаю такие команды вне сценария.\n\n"
        "Пожалуйста, нажмите /start и выберите валюту с помощью кнопок ниже, "
        "чтобы получить курс"
    )

#обработка ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

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
    application.add_handler(conv_handler)

# Другие команды
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("custom", custom_command))

# Ответы на текстовые сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Обработка ошибок
    application.add_error_handler(error)

    print("Опрашиваем...", flush=True)
    application.run_polling(drop_pending_updates=True, poll_interval=3)
if __name__ == "__main__":
    main()


