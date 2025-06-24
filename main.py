from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os

# 🎬 Kinolar (video file_id larini shu yerga joylang)
MOVIES = {
    "Avatar 2": "BQACAgQAAxkBAAIHrmYpEp_O7ShyHoO0AcbdCVZUPwz_AAJyUjEblXIBUfImv1PY_gp3AQADAgADeQADNAQ",
    "John Wick 4": "BQACAgQAAxkBAAIHq2YpEq3a3vnLrWZk1sj3KxXPUA4aAAJwUjEblXIB0vYH0uNjHDIzAQADAgADeQADNAQ"
}

# 🟢 /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Obuna bo‘ldingiz!\n🎬 Mana sizga birinchi kino:"
    )
    
    # 🔰 Avtomatik 1-kino yuborish
    first_title = list(MOVIES.keys())[0]
    await context.bot.send_video(
        chat_id=chat_id,
        video=MOVIES[first_title],
        caption=f"🎬 {first_title}"
    )

    # 📍 Tugma bilan kino tanlash
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=title)]
        for title in MOVIES
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text="Yana kino tanlang 👇",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# 🔘 Tugmani bosganda kino yuborish
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    title = query.data
    video_id = MOVIES.get(title)

    if video_id:
        await query.message.reply_video(video=video_id, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# 🚀 Botni ishga tushirish
async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot ishga tushdi...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
