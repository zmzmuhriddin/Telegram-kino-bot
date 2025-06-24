from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MOVIES = {
    "Avatar 2": "BAACAgQAAxkBAAIYgWZkKDxKH2Q",
    "John Wick 4": "BAACAgQAAxkBAAIYg2ZkKD0LHY",
}

USERS = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    USERS.add(user.id)

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
    reply_markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yana kino tanlang 👇",
        reply_markup=reply_markup
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

async def sendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz.")
        return

    if not context.args:
        await update.message.reply_text("Foydalanuvchilarga yuborish uchun matn yozing.")
        return

    message = " ".join(context.args)
    count = 0
    for user_id in USERS:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            count += 1
        except Exception as e:
            print(f"❌ Yuborilmadi: {user_id} - {e}")

    await update.message.reply_text(f"✅ Yuborildi: {count} foydalanuvchiga.")

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sendall", sendall))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot ishga tushdi...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
    import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Bu platformalarda mavjud bo‘lgan event loop uchun
        if str(e).startswith("Cannot close a running event loop"):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise
