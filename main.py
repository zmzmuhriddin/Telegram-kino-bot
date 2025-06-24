import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

from dotenv import load_dotenv
import nest_asyncio
import asyncio

# .env faylni yuklab olish
load_dotenv()

# Kinolar (video ID yoki havola)
MOVIES = {
    "Avatar 2": "https://example.com/video1.mp4",  # bu yerga haqiqiy link yoki file_id yozing
    "John Wick 4": "https://example.com/video2.mp4"
}

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Obuna bo‘ldingiz!\n🎬 Mana sizga birinchi kino:"
    )
    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=MOVIES["Avatar 2"],
        caption="🎬 Avatar 2"
    )

    # Kino tugmalari
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=title)]
        for title in MOVIES
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yana kino tanlang 👇",
        reply_markup=reply_markup
    )

# Tugma bosilganda kino yuborish
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video = MOVIES.get(title)
    if video:
        await query.message.reply_video(video=video, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("Kino topilmadi.")

# Botni ishga tushurish funksiyasi
async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot ishga tushdi...")
    await app.run_polling()

# asyncio muammosini hal qilish
nest_asyncio.apply()

if __name__ == "__main__":
    asyncio.run(main())
