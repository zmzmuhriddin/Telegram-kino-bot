import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes
)

# Muhit o‘zgaruvchilarni yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # .env da qo‘shilgan bo‘lishi kerak

# 🎥 Kinolar (video ID yoki havola)
MOVIES = {
    "Avatar 2": "https://t.me/your_channel/123",   # mana bu yerga to‘g‘ri link yoki video ID
    "John Wick 4": "https://t.me/your_channel/456"
}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text("✅ Obuna bo‘ldingiz!\n🎬 Mana sizga birinchi kino:")
    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=MOVIES["Avatar 2"],
        caption="🎬 Avatar 2"
    )

    # 🎬 Tugmalar
    buttons = [
        [InlineKeyboardButton(text=title, callback_data=title)]
        for title in MOVIES
    ]
    await update.message.reply_text(
        "Yana kino tanlang 👇",
        reply_markup=InlineKeyboardMarkup(buttons)
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

# 👑 Admin komandasi (masalan /stats)
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz admin emassiz!")
        return
    await update.message.reply_text("📊 Foydalanuvchilar statistikasi: ... (hozircha yo‘q)")

# Botni ishga tushirish
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("stats", stats))

    print("✅ Bot ishga tushdi...")
    await app.run_polling()

# Asinxron muhit bilan muammo chiqmasligi uchun maxsus ishlov
if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e).startswith("This event loop is already running"):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise
