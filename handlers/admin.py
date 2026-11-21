"""
Handlers for admin and super admin operations:
- Add movie (/addmovie & quick mode)
- Delete movie (/delmovie <code>)
- List recent movies (/listmovies)
- Stats (/stats)
- Broadcast message (/broadcast)
- Super Admin: /addadmin, /deladmin, /admins
"""

import asyncio
import logging
from typing import Optional, Tuple
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, BadRequest, TelegramError
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import SUPER_ADMIN_ID
from database import (
    add_admin,
    add_movie,
    delete_movie_by_code,
    get_all_admins,
    get_all_user_ids,
    get_recent_movies,
    get_stats,
    is_admin,
    is_super_admin,
    remove_admin,
)

logger = logging.getLogger(__name__)

# Conversation states for /addmovie
WAITING_FILE, WAITING_CODE, WAITING_TITLE = range(3)

# Conversation state for /broadcast
WAITING_BROADCAST_MESSAGE = range(1)


def validate_code(code: str) -> Tuple[bool, str]:
    """Validate movie code according to security rules."""
    code = code.strip()
    if not code:
        return False, "Kod bo'sh bo'lishi mumkin emas."
    if " " in code:
        return False, "Kino kodida bo'sh joy (probel) bo'lmasligi kerak."
    if len(code) > 20:
        return False, "Kino kodi 20 belgidan oshmasligi kerak."
    return True, code


# ================= Permission Checks ================= #

def check_admin(update: Update) -> bool:
    """Check if the user has admin rights. If not, silently ignore (no response)."""
    user = update.effective_user
    if not user:
        return False
    return is_admin(user.id)


def check_super_admin(update: Update) -> bool:
    """Check if the user is SUPER_ADMIN. If not, silently ignore."""
    user = update.effective_user
    if not user:
        return False
    return is_super_admin(user.id)


# ================= Quick Add Mode ================= #

async def quick_add_movie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle direct video/document upload with caption formatted as:
    code | title
    """
    if not check_admin(update):
        return

    message = update.message
    if not message or not message.caption:
        return

    caption = message.caption.strip()
    if "|" not in caption:
        return

    parts = caption.split("|", 1)
    raw_code = parts[0].strip()
    raw_title = parts[1].strip()

    is_valid, validation_msg = validate_code(raw_code)
    if not is_valid:
        await message.reply_text(f"❌ Xatolik: {validation_msg}")
        return

    if not raw_title:
        await message.reply_text("❌ Kino nomi kiritilmadi. Format: <code>kod | nom</code>", parse_mode=ParseMode.HTML)
        return

    if message.video:
        file_id = message.video.file_id
        file_type = "video"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
    else:
        return

    success, msg = add_movie(
        code=validation_msg,
        title=raw_title,
        file_id=file_id,
        file_type=file_type,
        added_by=update.effective_user.id,
    )

    if success:
        await message.reply_text(
            f"✅ <b>Kino saqlandi!</b>\n\n"
            f"🎬 Nomi: <b>{raw_title}</b>\n"
            f"🔑 Kodi: <code>{validation_msg}</code>\n"
            f"📁 Turi: {file_type}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.reply_text(f"❌ {msg}")


# ================= /addmovie Conversation ================= #

async def addmovie_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the /addmovie conversation flow."""
    if not check_admin(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "📹 Iltimos, kino <b>video</b> yoki <b>fayl (document)</b>ini yuboring.\n\n"
        "Jarayonni bekor qilish uchun /cancel buyrug'ini yuboring.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_FILE


async def addmovie_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the movie file and ask for the code."""
    message = update.message
    if message.video:
        context.user_data["movie_file_id"] = message.video.file_id
        context.user_data["movie_file_type"] = "video"
    elif message.document:
        context.user_data["movie_file_id"] = message.document.file_id
        context.user_data["movie_file_type"] = "document"
    else:
        await message.reply_text("Iltimos, video yoki fayl yuboring.")
        return WAITING_FILE

    await message.reply_text(
        "🔑 Endi kinoga beriladigan <b>kod</b>ni yuboring (masalan: <code>101</code>).\n"
        "Eslatma: kodda probel bo'lmasligi va maksimal 20 belgi bo'lishi lozim.",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_CODE


async def addmovie_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive code, validate it, and ask for the title."""
    text = update.message.text or ""
    is_valid, result = validate_code(text)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {result}\nIltimos, qaytadan boshqa kod kiriting yoki bekor qilish uchun /cancel yuboring."
        )
        return WAITING_CODE

    context.user_data["movie_code"] = result
    await update.message.reply_text(
        f"📝 Kod qabul qilindi: <code>{result}</code>\n\n"
        "Endi kinoning <b>nomi (sarlavhasi)</b>ni yuboring (masalan: <i>Forsaj 10 (2023)</i>):",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_TITLE


async def addmovie_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive title and save to database."""
    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text("Kino nomi bo'sh bo'lishi mumkin emas. Iltimos, nomini yozing:")
        return WAITING_TITLE

    code = context.user_data.get("movie_code")
    file_id = context.user_data.get("movie_file_id")
    file_type = context.user_data.get("movie_file_type")

    if not (code and file_id and file_type):
        await update.message.reply_text("Xatolik yuz berdi. Iltimos, /addmovie ni boshidan boshlang.")
        context.user_data.clear()
        return ConversationHandler.END

    success, msg = add_movie(
        code=code,
        title=title,
        file_id=file_id,
        file_type=file_type,
        added_by=update.effective_user.id,
    )

    if success:
        await update.message.reply_text(
            f"✅ <b>Kino muvaffaqiyatli saqlandi!</b>\n\n"
            f"🎬 Nomi: <b>{title}</b>\n"
            f"🔑 Kodi: <code>{code}</code>\n"
            f"📁 Turi: {file_type}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(f"❌ {msg}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any active conversation."""
    context.user_data.clear()
    await update.message.reply_text("Amal bekor qilindi.")
    return ConversationHandler.END


# ================= Delete Movie ================= #

async def delmovie_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delmovie <code>."""
    if not check_admin(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Foydalanish: <code>/delmovie &lt;kod&gt;</code>\nMasalan: <code>/delmovie 101</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    code = context.args[0].strip()
    if delete_movie_by_code(code):
        await update.message.reply_text(f"✅ <code>{code}</code> kodli kino bazadan o'chirildi.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ <code>{code}</code> kodli kino topilmadi.", parse_mode=ParseMode.HTML)


# ================= List Movies ================= #

async def listmovies_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /listmovies - show last 20 movies."""
    if not check_admin(update):
        return

    movies = get_recent_movies(limit=20)
    if not movies:
        await update.message.reply_text("Bazada hozircha birorta ham kino mavjud emas.")
        return

    lines = ["🎬 <b>Oxirgi 20 ta kino ro'yxati:</b>\n"]
    for i, m in enumerate(movies, start=1):
        lines.append(f"{i}. <code>{m['code']}</code> — <b>{m['title']}</b>")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


# ================= Stats ================= #

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command."""
    if not check_admin(update):
        return

    stats = get_stats()
    text = (
        "📊 <b>Bot statistikasi:</b>\n\n"
        f"🎬 Kinolar soni: <b>{stats['movies']}</b>\n"
        f"👤 Foydalanuvchilar: <b>{stats['users']}</b>\n"
        f"👮‍♂️ Adminlar soni: <b>{stats['admins']}</b>"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ================= Broadcast ================= #

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start /broadcast command."""
    if not check_admin(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n"
        "Xabar matn, rasm, video yoki fayl shaklida bo'lishi mumkin.\n\n"
        "Bekor qilish uchun /cancel yuboring."
    )
    return WAITING_BROADCAST_MESSAGE


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Forward/copy the broadcast message to all users."""
    message = update.message
    user_ids = get_all_user_ids()

    if not user_ids:
        await message.reply_text("Bazada foydalanuvchilar mavjud emas.")
        return ConversationHandler.END

    status_msg = await message.reply_text(f"🚀 Xabar {len(user_ids)} ta foydalanuvchiga yuborilmoqda...")

    sent_count = 0
    blocked_count = 0
    failed_count = 0

    for uid in user_ids:
        try:
            await message.copy(chat_id=uid)
            sent_count += 1
            await asyncio.sleep(0.04)  # Respect Telegram rate limits (~25-30 msg/sec)
        except Forbidden:
            blocked_count += 1
        except BadRequest as e:
            logger.warning("Broadcast BadRequest for user %s: %s", uid, e)
            failed_count += 1
        except TelegramError as e:
            logger.warning("Broadcast TelegramError for user %s: %s", uid, e)
            failed_count += 1
        except Exception as e:
            logger.error("Unexpected broadcast error for user %s: %s", uid, e)
            failed_count += 1

    result_text = (
        "✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"📨 Yuborildi: <b>{sent_count}</b>\n"
        f"🚫 Botni bloklaganlar: <b>{blocked_count}</b>\n"
        f"⚠️ Xatoliklar: <b>{failed_count}</b>"
    )
    try:
        await status_msg.edit_text(result_text, parse_mode=ParseMode.HTML)
    except Exception:
        await message.reply_text(result_text, parse_mode=ParseMode.HTML)

    return ConversationHandler.END


# ================= Super Admin Commands ================= #

def _extract_user_id_arg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Extract user_id from command args or replied message."""
    message = update.message
    if not message:
        return None

    # Check replied message
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    # Check arguments
    if context.args:
        try:
            return int(context.args[0].strip())
        except ValueError:
            return None
    return None


async def addadmin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Super Admin: /addadmin <user_id> or by replying to user's message."""
    if not check_super_admin(update):
        return

    target_id = _extract_user_id_arg(update, context)
    if not target_id:
        await update.message.reply_text(
            "Foydalanish:\n"
            "1. <code>/addadmin &lt;user_id&gt;</code>\n"
            "2. Yoki foydalanuvchining xabariga javob qilib <code>/addadmin</code> deb yozing.",
            parse_mode=ParseMode.HTML,
        )
        return

    if target_id == SUPER_ADMIN_ID:
        await update.message.reply_text("Bu foydalanuvchi allaqachon Super Admin hisoblanadi.")
        return

    if add_admin(target_id, added_by=update.effective_user.id):
        await update.message.reply_text(f"✅ Foydalanuvchi <code>{target_id}</code> admin etib tayinlandi.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"Foydalanuvchi <code>{target_id}</code> allaqachon admin.", parse_mode=ParseMode.HTML)


async def deladmin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Super Admin: /deladmin <user_id>."""
    if not check_super_admin(update):
        return

    target_id = _extract_user_id_arg(update, context)
    if not target_id:
        await update.message.reply_text(
            "Foydalanish: <code>/deladmin &lt;user_id&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    if target_id == SUPER_ADMIN_ID:
        await update.message.reply_text("❌ Super Adminni o'chirib bo'lmaydi!")
        return

    if remove_admin(target_id):
        await update.message.reply_text(f"✅ Foydalanuvchi <code>{target_id}</code> adminlikdan olindi.", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ Foydalanuvchi <code>{target_id}</code> adminlar ro'yxatida topilmadi.", parse_mode=ParseMode.HTML)


async def admins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Super Admin: /admins - list all admins."""
    if not check_super_admin(update):
        return

    admins = get_all_admins()
    lines = ["👮‍♂️ <b>Adminlar ro'yxati:</b>\n"]
    lines.append(f"👑 <b>Super Admin:</b> <code>{SUPER_ADMIN_ID}</code>\n")

    if admins:
        lines.append("🔹 <b>Qo'shilgan adminlar:</b>")
        for i, a in enumerate(admins, start=1):
            lines.append(f"{i}. <code>{a['user_id']}</code> (qo'shdi: <code>{a['added_by']}</code>)")
    else:
        lines.append("Hozircha qo'shimcha adminlar yo'q.")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin help / command menu when /admin is called."""
    if not check_admin(update):
        return

    user_id = update.effective_user.id
    is_super = is_super_admin(user_id)

    role_text = "👑 Super Admin" if is_super else "👮‍♂️ Admin"

    text = (
        f"🔐 <b>Admin Boshqaruv Paneli</b> ({role_text})\n\n"
        "🎬 <b>Kino boshqaruvi:</b>\n"
        "• /addmovie — Yangi kino yuklash\n"
        "• /delmovie &lt;kod&gt; — Kinoni o'chirish\n"
        "• /listmovies — Oxirgi 20 ta kinoni ko'rish\n"
        "• <i>Tezkor yuklash:</i> Videoga <code>kod | nom</code> deb caption yozib yuboring\n\n"
        "📊 <b>Statistika va xabarlar:</b>\n"
        "• /stats — Bot statistikasi\n"
        "• /broadcast — Barcha foydalanuvchilarga xabar yuborish\n"
    )

    if is_super:
        text += (
            "\n👑 <b>Super Admin buyruqlari:</b>\n"
            "• /addadmin &lt;user_id&gt; — Yangi admin qo'shish\n"
            "• /deladmin &lt;user_id&gt; — Adminni o'chirish\n"
            "• /admins — Adminlar ro'yxatini ko'rish\n"
        )

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

