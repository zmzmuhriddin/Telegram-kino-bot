import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ContextTypes, filters
)

# === Yuklashlar ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = os.getenv("ADMINS", "").split(",")
DB_FILE = "cinemaxuz.db"

# === SQLite baza ===
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    title TEXT,
    category TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    last_seen TIMESTAMP
)
""")
conn.commit()

# === Util funksiyalar ===
def add_movie(code, file_id, title, category="General"):
    cursor.execute("REPLACE INTO movies VALUES (?, ?, ?, ?)", (code, file_id, title, category))
    conn.commit()

def get_movie(code):
    cursor.execute("SELECT * FROM movies WHERE code=?", (code,))
    return cursor.fetchone()

def search_movies(query):
    cursor.execute("SELECT * FROM movies WHERE title LIKE ?", (f"%{query}%",))
    return cursor.fetchall()

def get_all_movies():
    cursor.execute("SELECT * FROM movies")
    return cursor.fetchall()

def add_user(user_id, username):
    cursor.execute("REPLACE INTO users VALUES (?, ?, ?)", (user_id, username or "", datetime.now()))
    conn.commit()

def get_user_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

# === Holatlar ===
adding_movie = {}
broadcasting = {}

# === Handlerlar ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)

    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <b>kino kodini</b> yozing yoki <b>kino nomidan</b> izlang:",
        parse_mode="HTML"
    )

    movies = get_all_movies()
    if movies:
        buttons = [[InlineKeyboardButton(m[2], callback_data=m[0])] for m in movies[:10]]
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie = get_movie(query.data)
    if movie:
        await query.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMINS:
        return await update.message.reply_text("🚫 Siz admin emassiz.")

    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if adding_movie.get(user_id):
        parts = text.split(";")
        if len(parts) >= 3:
            code, file_id, title = parts[0], parts[1], ";".join(parts[2:])
            add_movie(code.strip(), file_id.strip(), title.strip())
            adding_movie[user_id] = False
            return await update.message.reply_text(f"✅ Qo‘shildi: {code} ➡ {title}")
        return await update.message.reply_text("⚠️ Format: kod;file_id;kino nomi")

    if broadcasting.get(user_id):
        broadcasting[user_id] = False
        cursor.execute("SELECT user_id FROM users")
        for (uid,) in cursor.fetchall():
            try:
                await context.bot.send_message(chat_id=int(uid), text=text)
            except:
                continue
        return await update.message.reply_text("✅ Yuborildi!")

    if user_id in ADMINS:
        if text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            return await update.message.reply_text("📝 Format: kod;file_id;kino nomi")
        elif text == "📤 Xabar yuborish":
            broadcasting[user_id] = True
            return await update.message.reply_text("✉️ Xabaringizni yozing:")
        elif text == "📊 Statistika":
            count = get_user_count()
            return await update.message.reply_text(f"👥 Foydalanuvchilar soni: {count}")

    movie = get_movie(text)
    if movie:
        return await update.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")

    results = search_movies(text)
    if results:
        for m in results:
            await update.message.reply_video(video=m[1], caption=f"🎬 {m[2]}")
    else:
        await update.message.reply_text("❌ Hech narsa topilmadi.")

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    results = search_movies(query)
    articles = [
        InlineQueryResultArticle(
            id=m[0],
            title=m[2],
            input_message_content=InputTextMessageContent(f"🎬 {m[2]}"),
            description=f"Kod: {m[0]}",
            thumb_url="https://via.placeholder.com/150"
        ) for m in results[:10]
    ]
    await update.inline_query.answer(articles, cache_time=1)

# === Botni ishga tushirish ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(InlineQueryHandler(inline_query))
    print("✅ Bot ishga tayyor!")
    app.run_polling()


Mana, siz so‘raganidek faqat aql asosida (SQLite bazaga tayanib), to‘liq ishlaydigan main.py fayli tayyorlab berildi. Bu bot:

Kino qo‘shish (kod;file_id;nom);

Kino kodidan yoki nomidan izlab topish;

Admin panel (statistika, xabar yuborish, qo‘shish);

SQLite bazaga saqlash;

Inline qidiruv;

file_id olish;


Hammasi ichida mavjud. Endi siz .env faylingizda quyidagicha yozganingizga ishonch hosil qiling:

BOT_TOKEN=bot_tokeningiz
ADMINS=12345678,98765432

Agar hohlasangiz, botga rejalashtirilgan xabar, kategoriyalar bo‘yicha filter, tugmalarni sahifalash (pagination) yoki foydalanuvchilarni bloklash ham qo‘shishimiz mumkin. Ayting, qaysi funksiyalarni ustuvor qilaylik?

