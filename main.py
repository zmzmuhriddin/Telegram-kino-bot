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

MOVIES = {
    "1": {"file_id": "VIDEO_FILE_ID_1", "title": "Avatar 2"},
    "2": {"file_id": "VIDEO_FILE_ID_2", "title": "John Wick 4"}
}

adding_movie = {}
broadcasting = {}
USERS_FILE = "users.txt"

def save_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(f"{user_id}\n")
    else:
        with open(USERS_FILE, "r") as f:
            users = f.read().splitlines()
        if str(user_id) not in users:
            with open(USERS_FILE, "a") as f:
                f.write(f"{user_id}\n")

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    save_user(user_id)

    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:",
        parse_mode="HTML"
    )
    buttons = [[InlineKeyboardButton(movie["title"], callback_data=code)] for code, movie in MOVIES.items()]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)

# Tugma bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data
    movie = MOVIES.get(code)
    if movie:
        await query.message.reply_video(video=movie["file_id"], caption=f"🎬 {movie['title']}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# /admin komandasi
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=markup)

# Matnli xabarlar
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Admin kino qo‘shmoqda
    if adding_movie.get(user_id):
        parts = text.split(";")
        if len(parts) == 3:
            code, file_id, title = parts
            MOVIES[code.strip()] = {
                "file_id": file_id.strip(),
                "title": title.strip()
            }
            adding_movie[user_id] = False
            await update.message.reply_text(f"✅ Kino qo‘shildi: {code.strip()} ➡ {title.strip()}")
        else:
            await update.message.reply_text("⚠️ Format noto‘g‘ri. Format: <code>1;file_id;Gladio</code>", parse_mode="HTML")
        return

    # Admin xabar yubormoqda
    if broadcasting.get(user_id):
        broadcasting[user_id] = False
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                users = f.read().splitlines()
            count = 0
            for uid in users:
                try:
                    await context.bot.send_message(chat_id=uid, text=text)
                    count += 1
                except:
                    pass
            await update.message.reply_text(f"✅ {count} ta foydalanuvchiga yuborildi.")
        else:
            await update.message.reply_text("⚠️ Foydalanuvchilar ro'yxati topilmadi.")
        return

    # Admin tugmalari
    if user_id == ADMIN_ID:
        if text == "📊 Statistika":
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f:
                    users = f.read().splitlines()
                await update.message.reply_text(f"👥 Obunachilar soni: {len(users)}")
            else:
                await update.message.reply_text("👥 Obunachilar soni: 0")
            return
        elif text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            await update.message.reply_text("📝 Format: <code>1;file_id;Gladio</code>", parse_mode="HTML")
            return
        elif text == "📤 Xabar yuborish":
            broadcasting[user_id] = True
            await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
            return

    # Kino kodi orqali
    movie = MOVIES.get(text)
    if movie:
        await update.message.reply_video(video=movie["file_id"], caption=f"🎬 {movie['title']}")
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
