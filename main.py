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

MOVIES = {
    "Avatar 2": "VIDEO_FILE_ID_1",
    "John Wick 4": "VIDEO_FILE_ID_2"
}

# 🔄 Bu flag admin kino qo‘shish holatini bildiradi
adding_movie = {}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:",
        parse_mode="HTML"
    )
    buttons = [[InlineKeyboardButton(title, callback_data=title)] for title in MOVIES]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)

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

# /admin komandasi
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=reply_markup)

# Yagona matn handler — admin yoki user
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Admin rejimida bo‘lsa va flag yoqilgan bo‘lsa
    if adding_movie.get(user_id):
        if ";" in text:
            title, file_id = text.split(";", 1)
            MOVIES[title.strip()] = file_id.strip()
            adding_movie[user_id] = False
            await update.message.reply_text(f"✅ Kino qo‘shildi: {title.strip()}")
        else:
            await update.message.reply_text(
                "⚠️ Noto‘g‘ri format. Quyidagicha yozing:\n<code>Kino nomi;file_id</code>",
                parse_mode="HTML"
            )
        return

    # Admin panel tugmalari
    if user_id == ADMIN_ID:
        if text == "📊 Statistika":
            await update.message.reply_text("👥 Obunachilar soni: 100+")
            return
        elif text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            await update.message.reply_text(
                "📝 Kino nomi va file_id ni quyidagicha yuboring:\n<code>Kino nomi;file_id</code>",
                parse_mode="HTML"
            )
            return
        elif text == "📤 Xabar yuborish":
            await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
            return

    # Odatdagi kino kodi
    video_id = MOVIES.get(text)
    if video_id:
        await update.message.reply_video(video=video_id, caption=f"🎬 {text}")
    else:
        await update.message.reply_text("❌ Bunday kino topilmadi.")

# file_id olish uchun
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 Video file_id:\n<code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring.")

# Botni ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
