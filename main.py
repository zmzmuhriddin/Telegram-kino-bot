import nest_asyncio
nest_asyncio.apply()

import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🎬 Kinolar ro‘yxati: nom va kodlar
MOVIES = {
    "Avatar 2": "VIDEO_FILE_ID_1",
    "John Wick 4": "VIDEO_FILE_ID_2",
    "1234": "VIDEO_FILE_ID_1",  # Kino kodi orqali ko‘rish
    "5678": "VIDEO_FILE_ID_2"
}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [[InlineKeyboardButton(title, callback_data=title)] for title in ["Avatar 2", "John Wick 4"]]
    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n"
            "🎥 Kino ko‘rish uchun tugmadan tanlang yoki kino <b>kodini yozing</b>:"
        ),
        reply_markup=markup,
        parse_mode="HTML"
    )

# Tugmani bosganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video_id = MOVIES.get(title)
    if video_id:
        await query.message.reply_video(video=video_id, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# Kod yozilganda avtomatik kino yuborish
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    video_id = MOVIES.get(text)
    if video_id:
        await update.message.reply_video(video=video_id, caption=f"🎬 Kino kodi orqali topildi")
    else:
        await update.message.reply_text("❌ Bunday kino kodi topilmadi. Tugmalardan foydalaning yoki to‘g‘ri kod kiriting.")

# Botni ishga tushirish
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot ishga tushdi...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
