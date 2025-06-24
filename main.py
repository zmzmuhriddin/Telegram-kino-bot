import os
import json
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
ADMINS = os.getenv("ADMINS", "").split(",")  # Misol: "12345,67890"
MOVIES_FILE = "movies.json"
USERS_FILE = "users.txt"

# Kinolarni yuklash
if os.path.exists(MOVIES_FILE):
    with open(MOVIES_FILE, "r") as f:
        MOVIES = json.load(f)
else:
    MOVIES = {}

adding_movie = {}
waiting_broadcast = {}

def save_movies():
    with open(MOVIES_FILE, "w") as f:
        json.dump(MOVIES, f, indent=2)

def add_user(user_id):
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE, "w").close()
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(user_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(str(user_id) + "\n")

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>",
        parse_mode="HTML"
    )
    buttons = [[InlineKeyboardButton(data['title'], callback_data=code)] for code, data in MOVIES.items()]
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
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=markup)

# Matnli handler
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Kino qo‘shish
    if adding_movie.get(user_id):
        parts = text.split(";")
        if len(parts) == 3:
            code, file_id, title = parts
            MOVIES[code.strip()] = {"file_id": file_id.strip(), "title": title.strip()}
            save_movies()
            adding_movie[user_id] = False
            await update.message.reply_text(f"✅ Kino qo‘shildi: {code.strip()} ➡ {title.strip()}")
        else:
            await update.message.reply_text("⚠️ Format noto‘g‘ri. Format: <code>1;file_id;kino_nomi</code>", parse_mode="HTML")
        return

    # Broadcast
    if waiting_broadcast.get(user_id):
        with open(USERS_FILE, "r") as f:
            users = f.read().splitlines()
        for uid in users:
            try:
                await context.bot.send_message(chat_id=int(uid), text=text)
            except:
                continue
        waiting_broadcast[user_id] = False
        await update.message.reply_text("✅ Xabar yuborildi!")
        return

    # Admin komandalar
    if user_id in ADMINS:
        if text == "📊 Statistika":
            with open(USERS_FILE, "r") as f:
                users = f.read().splitlines()
            await update.message.reply_text(f"👥 Obunachilar soni: {len(users)} ta")
            return
        elif text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            await update.message.reply_text(
                "📝 Format: <code>kod;file_id;kino_nomi</code>\nMisol: <code>1;BAACAgIA...;Gladio</code>",
                parse_mode="HTML"
            )
            return
        elif text == "📤 Xabar yuborish":
            waiting_broadcast[user_id] = True
            await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
            return

    # Foydalanuvchi kino kodi kiritdi
    movie = MOVIES.get(text)
    if movie:
        await update.message.reply_video(video=movie["file_id"], caption=f"🎬 {movie['title']}")
    else:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

# file_id olish
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 Video file_id:\n<code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring.")

# Ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
