from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
import os

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Kinolar (video fayl ID yoki havolani qo'yasiz)
MOVIES = {
    "Avatar 2": "https://example.com/avatar2.mp4",
    "John Wick 4": "https://example.com/johnwick4.mp4"
}

# /start komandasi
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

    # Tugmalar
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=title)]
        for title in MOVIES
    ]
    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yana kino tanlang 👇",
        reply_markup=markup
    )

# Kino tugmasini bosganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video = MOVIES.get(title)
    if video:
        await query.message.reply_video(video=video, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("Kino topilmadi.")

# /stats komandasi faqat admin uchun
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        await update.message.reply_text("📊 Statistika: Foydalanuvchilar soni: ??? (keyin yozamiz)")
    else:
        await update.message.reply_text("⛔ Sizda ruxsat yo‘q.")

# Asosiy ishga tushirish
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot ishga tushdi...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
