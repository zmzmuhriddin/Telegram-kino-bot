from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import os

# Kinolar (video fayl IDlarini o'zingizniki bilan almashtiring)
MOVIES = {
    "Dunyoning yaratilishi": "https://t.me/zokirov_muxriddin/6",
    "Hamid": "https://t.me/zokirov_muxriddin/14",
}

# Start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # ✅ Avtomatik birinchi kinoni yuborish
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✅ Obuna bo‘ldingiz!\n🎬 Mana sizga birinchi kino:"
    )
    await context.bot.send_video(
        chat_id=update.effective_chat.id,
        video=MOVIES["Dunyoning yaratilishi"],  # Birinchi avtomatik kino
        caption="🎬 Dunyoning yaratilishi"
    )

    # 🎬 Tugmalar bilan kino ro‘yxatini chiqarish
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

# Tugmani bosganda kino yuborish
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video_id = MOVIES.get(title)
    if video_id:
        await query.message.reply_video(video=video_id, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("Kino topilmadi.")

# Botni ishga tushirish
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
