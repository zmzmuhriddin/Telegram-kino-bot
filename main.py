from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os

# Kinolar (video fayl IDlarini o'zingiz kiriting)
MOVIES = {
    "Avatar 2": "BQACAgQAAxkBAAIeX2YH...",  # bu yerga haqiqiy file_id yoziladi
    "John Wick 4": "BQACAgQAAxkBAAIeYGZH...", 
}

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
    buttons = [[InlineKeyboardButton(text=title, callback_data=title)] for title in MOVIES]
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yana kino tanlang 👇",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video_id = MOVIES.get(title)
    if video_id:
        await query.message.reply_video(video=video_id, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("Kino topilmadi.")

def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
