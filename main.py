import nest_asyncio
nest_asyncio.apply()

import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# 🎥 Kino ro'yxati (ID yoki havola)
MOVIES = {
    "Avatar 2": "VIDEO_FILE_ID_1",
    "John Wick 4": "VIDEO_FILE_ID_2",
    # "Kod123": "VIDEO_FILE_ID_3", kabi qo‘shishingiz mumkin
}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.application.chat_data[chat_id] = True  # foydalanuvchini saqlash

    await context.bot.send_message(
        chat_id=chat_id,
        text="🎬 *CinemaxUZ botiga xush kelibsiz!*\n\n🎥 Kino ko‘rish uchun tugmadan tanlang yoki kino *kodini yozing*:",
        parse_mode="Markdown"
    )

    # Tugmalar
    buttons = [[InlineKeyboardButton(title, callback_data=title)] for title in MOVIES]
    markup = InlineKeyboardMarkup(buttons)

    await context.bot.send_message(
        chat_id=chat_id,
        text="👇 Kino ro‘yxati:",
        reply_markup=markup
    )

# Tugmalarni bosganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    video_id = MOVIES.get(title)
    if video_id:
        await query.message.reply_video(video=video_id, caption=f"🎬 {title}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# Matn yozilganda — kino kodi
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    video_id = MOVIES.get(text)
    if video_id:
        await update.message.reply_video(video=video_id, caption=f"🎬 {text}")
    else:
        await update.message.reply_text("😔 Bunday kod bilan kino topilmadi.")

# /admin komandasi
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id == ADMIN_ID:
        total_users = len(context.application.chat_data)
        await update.message.reply_text(
            f"👨‍💻 *Admin panel:*\n\n"
            f"👥 Obunachilar: {total_users}\n"
            f"🎞 Kinolar soni: {len(MOVIES)}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Sizda ruxsat yo‘q.")

# Botni ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
