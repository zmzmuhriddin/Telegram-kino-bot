import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # ixtiyoriy bo'lsa, int ga aylantiring: int(os.getenv("ADMIN_ID"))

# Kinolar ro'yxati (video linklar yoki fayl IDlar)
MOVIES = {
    "Avatar 2": "https://t.me/your_channel/123",  # bu yerga haqiqiy video havola
    "John Wick 4": "https://t.me/your_channel/456",
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
    buttons = [[InlineKeyboardButton(text=title, callback_data=title)] for title in MOVIES]
    markup = InlineKeyboardMarkup(buttons)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Yana kino tanlang 👇",
        reply_markup=markup
    )

# Tugmalarni bosganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video = MOVIES.get(title)
    if video:
        await query.message.reply_video(video=video, caption=f"🎬 {title}")
