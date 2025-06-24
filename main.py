import os
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

nest_asyncio.apply()
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# 🎬 Kinolar ro'yxati
MOVIES = {
    "Avatar 2": "VIDEO_FILE_ID_1",
    "John Wick 4": "VIDEO_FILE_ID_2"
}

# Flag - admin kino qo‘shish rejimida yoki yo‘q
adding_movie = False

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:",
        parse_mode="HTML"
    )
    buttons = [[InlineKeyboardButton(title, callback_data=title)] for title in MOVIES]
    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🎬 Mavjud kinolar:",
        reply_markup=markup
    )

# Tugma bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video_id = MOVIES.get(title)
    if video_id:
        await query.message.reply_video(video=video_id, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# Kino kodi orqali yoki admin rejimida
async def movie_by_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global adding_movie
    text = update.message.text.strip()

    # Admin kino qo‘shayotgan bo‘lsa
    if adding_movie and str(update.effective_user.id) == ADMIN_ID:
        if ";" in text:
            title, file_id = text.split(";", 1)
            MOVIES[title.strip()] = file_id.strip()
            adding_movie = False
            await update.message.reply_text(f"✅ Kino qo‘shildi: {title.strip()}")
        else:
            await update.message.reply_text(
                "⚠️ Noto‘g‘ri format. Quyidagicha yozing:\n<code>Kino nomi;file_id</code>",
                parse_mode="HTML"
            )
        return

    # Oddiy foydalanuvchi kodi
    video_id = MOVIES.get(text)
    if video_id:
        await update.message.reply_video(video=video_id, caption=f"🎬 {text}")
    else:
        await update.message.reply_text("❌ Bunday kino topilmadi.")

# Admin komandasi
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [
        ["📊 Statistika", "➕ Kino qo‘shish"],
        ["📤 Xabar yuborish"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "👑 Admin panelga xush kelibsiz! Quyidagilardan birini tanlang:",
        reply_markup=reply_markup
    )

# Admin tugmalarini boshqarish
async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global adding_movie
    if str(update.effective_user.id) != ADMIN_ID:
        return

    text = update.message.text
    if text == "📊 Statistika":
        await update.message.reply_text("👥 Obunachilar soni: 100+")
    elif text == "➕ Kino qo‘shish":
        adding_movie = True
        await update.message.reply_text(
            "📝 Kino nomi va file_id ni quyidagicha yuboring:\n<code>Kino nomi;file_id</code>",
            parse_mode="HTML"
        )
    elif text == "📤 Xabar yuborish":
        await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
    else:
        await update.message.reply_text("⚠️ Nomaʼlum buyruq.")

# file_id olish uchun video yuborish
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(
            f"🎬 Video file_id:\n<code>{file_id}</code>", parse_mode="HTML"
        )
    else:
        await update.message.reply_text("❌ Video yuboring.")

# Botni ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, movie_by_code))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
