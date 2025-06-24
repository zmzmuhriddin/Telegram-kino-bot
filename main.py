import os
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

nest_asyncio.apply()
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Kino kodi: (file_id, real title)
MOVIES = {
    "1": ("VIDEO_FILE_ID_1", "Avatar 2"),
    "2": ("VIDEO_FILE_ID_2", "John Wick 4")
}

# Adminlar qo‘shmoqchi bo‘lgan kino holati
adding_movie = {}

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:",
        parse_mode="HTML"
    )
    buttons = [[InlineKeyboardButton(title, callback_data=title)] for title in MOVIES]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)

# Tugmadan kino yuborish
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    title = query.data
    movie = MOVIES.get(title)
    if movie:
        file_id, real_title = movie
        await query.message.reply_video(video=file_id, caption=f"🎬 {real_title}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# Admin paneli
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=reply_markup)

# Yagona matn handler - admin yoki user
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Admin kino qo‘shayotgan bo‘lsa
    if adding_movie.get(user_id):
        if ";" in text:
            key, value = text.split(";", 1)
            code = key.strip()              # masalan: "1"
            file_id_and_title = value.strip().split(",", 1)
            if len(file_id_and_title) == 2:
                file_id, real_title = file_id_and_title
                MOVIES[code] = (file_id.strip(), real_title.strip())
                adding_movie[user_id] = False
                await update.message.reply_text(f"✅ Kino qo‘shildi: {real_title.strip()} ({code})")
            else:
                await update.message.reply_text("⚠️ Format noto‘g‘ri. To‘g‘ri format: <code>1;file_id,Gladio</code>", parse_mode="HTML")
        else:
            await update.message.reply_text("⚠️ Format noto‘g‘ri. To‘g‘ri format: <code>1;file_id,Gladio</code>", parse_mode="HTML")
        return

    # Admin tugmalari
    if user_id == ADMIN_ID:
        if text == "📊 Statistika":
            await update.message.reply_text("👥 Obunachilar soni: 100+")
            return
        elif text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            await update.message.reply_text("📝 Yangi kino qo‘shish uchun yozing:\n<code>1;file_id,Gladio</code>", parse_mode="HTML")
            return
        elif text == "📤 Xabar yuborish":
            await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
            return

    # Foydalanuvchi kod kiritgan bo‘lsa
    movie = MOVIES.get(text)
    if movie:
        file_id, real_title = movie
        await update.message.reply_video(video=file_id, caption=f"🎬 {real_title}")
    else:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

# file_id olish uchun
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id:\n<code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring.")

# Botni ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
