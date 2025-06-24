import os
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    MessageHandler, filters
)

# Async loop xatolarini hal qiladi
nest_asyncio.apply()

# .env fayldan tokenlarni o‘qish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Kinolar (kod orqali va tugmalar orqali)
MOVIES = {
    "123456": {
        "title": "Avatar 2",
        "video": "VIDEO_FILE_ID_1"
    },
    "654321": {
        "title": "John Wick 4",
        "video": "VIDEO_FILE_ID_2"
    }
}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *CinemaxUZ botiga xush kelibsiz!*\n\n"
        "🎥 Kino ko‘rish uchun tugmadan tanlang yoki kino *kodini yozing*:",
        parse_mode="Markdown"
    )

    # Tugmalar orqali kino tanlash
    buttons = [[InlineKeyboardButton(data['title'], callback_data=key)] for key, data in MOVIES.items()]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("👇 Quyidagilardan birini tanlang:", reply_markup=markup)

# Tugmadan kino tanlansa
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie_key = query.data
    movie = MOVIES.get(movie_key)
    if movie:
        await query.message.reply_video(video=movie["video"], caption=f"🎬 {movie['title']}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# Foydalanuvchi kino kodi yozsa
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    movie = MOVIES.get(user_input)
    if movie:
        await update.message.reply_video(video=movie["video"], caption=f"🎬 {movie['title']}")
    else:
        await update.message.reply_text("❌ Bunday kino kodi topilmadi.")

# Botni ishga tushirish
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ CinemaxUZ bot ishga tushdi...")
    app.run_polling()
