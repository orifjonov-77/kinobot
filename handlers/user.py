"""
Handlers for regular users: /start, /help, and movie lookup by code.
"""

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from database import add_or_update_user, get_movie_by_code

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = update.effective_user
    if not user:
        return

    add_or_update_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    welcome_text = (
        f"Assalomu alaykum, <b>{user.first_name}</b>!\n\n"
        "🎬 <b>Kino Botiga xush kelibsiz!</b>\n\n"
        "Kinoni tomosha qilish uchun uning kodini yuboring (masalan: <code>101</code>).\n"
        "Qo'shimcha ma'lumot olish uchun /help buyrug'idan foydalaning."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.HTML)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    user = update.effective_user
    if user:
        add_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    help_text = (
        "ℹ️ <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1. Kinoni yuklab olish uchun uning kodini matn shaklida yuboring (masalan: <code>123</code>).\n"
        "2. Agar kod to'g'ri bo'lsa, bot sizga kinoni yuboradi.\n"
        "3. Agar kino topilmasa, bot bu haqida xabar beradi.\n\n"
        "Savol yoki takliflar bo'lsa, adminga murojaat qiling."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


async def movie_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages to search for movies by code."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    if user:
        add_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    code = update.message.text.strip()

    # If the message looks like a command, ignore here (handled by other handlers)
    if code.startswith("/"):
        return

    movie = get_movie_by_code(code)
    if not movie:
        await update.message.reply_text("Bunday kodli kino topilmadi.")
        return

    file_id = movie["file_id"]
    file_type = movie["file_type"]
    title = movie["title"]
    caption = f"🎬 <b>{title}</b>\n🔑 Kod: <code>{movie['code']}</code>"

    try:
        if file_type == "video":
            await update.message.reply_video(
                video=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
        else:
            await update.message.reply_document(
                document=file_id,
                caption=caption,
                parse_mode=ParseMode.HTML,
            )
    except Exception as e:
        logger.error("Error sending movie file: %s", e)
        await update.message.reply_text(
            "Kino faylini yuborishda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )
