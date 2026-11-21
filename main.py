"""
Main entry point for the Telegram Movie Bot.
Configures logging, database, error handler, and registers all handlers.
"""

import html
import json
import logging
import sys
import traceback
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import NetworkError, RetryAfter, TimedOut
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, LOG_FILE
from database import init_db
from handlers.admin import (
    WAITING_BROADCAST_MESSAGE,
    WAITING_CODE,
    WAITING_FILE,
    WAITING_TITLE,
    addadmin_handler,
    admin_panel_handler,
    addmovie_code,
    addmovie_file,
    addmovie_start,
    addmovie_title,
    admins_handler,
    broadcast_send,
    broadcast_start,
    cancel_handler,
    deladmin_handler,
    delmovie_handler,
    listmovies_handler,
    quick_add_movie_handler,
    stats_handler,
)
from handlers.user import help_handler, movie_search_handler, start_handler

# Configure logging to console and file (bot.log)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and inform the user if possible."""
    error = context.error
    logger.error("Exception while handling an update: %s", error)

    # Specific handling for network and timeout errors
    if isinstance(error, (NetworkError, TimedOut)):
        logger.warning("Network issue encountered: %s. Handled with automatic retry in PTB.", error)
        return

    if isinstance(error, RetryAfter):
        logger.warning("Flood control exceeded. Retry in %s seconds.", error.retry_after)
        return

    # Log full traceback
    tb_list = traceback.format_exception(None, error, error.__traceback__)
    tb_string = "".join(tb_list)
    logger.error("Traceback:\n%s", tb_string)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Kechirasiz, buyruqni bajarishda kutilmagan xatolik yuz berdi. "
                "Iltimos, birozdan so'ng qayta urinib ko'ring."
            )
        except Exception as e:
            logger.error("Failed to send error notification message: %s", e)


def main() -> None:
    """Initialize database and start the bot polling."""
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("\n[XATOLIK] BOT_TOKEN sozlanmagan!")
        print("Iltimos, '.env' faylini oching va BOT_TOKEN qiymatini kiriting.")
        print("Namuna: BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ\n")
        sys.exit(1)

    # Initialize SQLite database tables
    init_db()
    logger.info("Database initialized successfully.")

    # Build Application
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .get_updates_connect_timeout(30.0)
        .get_updates_read_timeout(30.0)
        .build()
    )

    # 1. /addmovie ConversationHandler
    addmovie_conv = ConversationHandler(
        entry_points=[CommandHandler("addmovie", addmovie_start)],
        states={
            WAITING_FILE: [
                MessageHandler(filters.VIDEO | filters.Document.ALL, addmovie_file)
            ],
            WAITING_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, addmovie_code)
            ],
            WAITING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, addmovie_title)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        per_user=True,
    )

    # 2. /broadcast ConversationHandler
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            WAITING_BROADCAST_MESSAGE: [
                MessageHandler(filters.ALL & ~filters.COMMAND, broadcast_send)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        per_user=True,
    )

    # Register Admin Handlers
    application.add_handler(addmovie_conv)
    application.add_handler(broadcast_conv)

    # Quick Add Movie (Admin uploads video/document with caption "code | title")
    application.add_handler(
        MessageHandler(
            (filters.VIDEO | filters.Document.ALL) & filters.CAPTION,
            quick_add_movie_handler,
        )
    )

    application.add_handler(CommandHandler("delmovie", delmovie_handler))
    application.add_handler(CommandHandler("listmovies", listmovies_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(CommandHandler("admin", admin_panel_handler))

    # Super Admin Handlers
    application.add_handler(CommandHandler("addadmin", addadmin_handler))
    application.add_handler(CommandHandler("deladmin", deladmin_handler))
    application.add_handler(CommandHandler("admins", admins_handler))

    # General User Handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))

    # Movie search by text code (must be added after commands)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, movie_search_handler)
    )

    # Global Error Handler
    application.add_error_handler(error_handler)

    logger.info("Bot ishga tushmoqda...")
    print("Bot muvaffaqiyatli ishga tushdi! To'xtatish uchun Ctrl+C bosing.")

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
