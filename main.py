import os
import json
import sqlite3
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes
)

# === TAYYORLOV ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = os.getenv("ADMINS", "").split(",")
DB_FILE = "cinemaxuz.db"

# === SQLite bazasini yaratish ===
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    title TEXT,
    category TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    last_seen TIMESTAMP
);
""")
conn.commit()

# === Funksiyalar ===
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

def get_movie_count():
    cursor.execute("SELECT COUNT(*) FROM movies")
    return cursor.fetchone()[0]

# === Holatlar ===
adding_movie = {}
broadcasting = {}

# === Start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)

    buttons = [
        [InlineKeyboardButton("🎬 Kinolar", callback_data="movies")],
        [InlineKeyboardButton("🔎 Qidiruv", callback_data="search")],
        [InlineKeyboardButton("ℹ️ Ma'lumot", callback_data="info")]
    ]
    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n"
        "🎥 Kino ko‘rish uchun <b>kino kodini</b> yozing yoki <b>kino nomidan</b> izlang.\n\n"
        "👇 Quyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=markup
    )

# === Button Handler ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "movies":
        movies = get_all_movies()
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=m[0])] for m in movies]
            markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)
        else:
            await query.message.reply_text("📭 Hozircha kinolar mavjud emas.")

    elif query.data == "search":
        await query.message.reply_text("🔎 Kino nomini yoki kodini yuboring, izlab topib beraman.")

    elif query.data == "info":
        await query.message.reply_text(
            "ℹ️ <b>Ma'lumot:</b>\n\n"
            "Bu bot orqali siz turli kinolarni topishingiz va tomosha qilishingiz mumkin.\n"
            "👨‍💻 Dasturchi: @Zokirov_cinemaxuz\n"
            "📅 Versiya: 1.0\n\n"
            "👉 Kino kodini yozing yoki qidiruvdan foydalaning.",
            parse_mode="HTML"
        )

    else:
        movie = get_movie(query.data)
        if movie:
            await query.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        else:
            await query.message.reply_text("❌ Kino topilmadi.")

# === Admin Panel ===
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMINS:
        return await update.message.reply_text("🚫 Siz admin emassiz.")
    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

# === Matnli Xabarlar ===
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Admin kino qo‘shmoqda
    if adding_movie.get(user_id):
        parts = text.split(";")
        if len(parts) >= 3:
            code, file_id, title = parts[0], parts[1], ";".join(parts[2:])
            add_movie(code.strip(), file_id.strip(), title.strip())
            adding_movie[user_id] = False
            return await update.message.reply_text(f"✅ Qo‘shildi: {code.strip()} ➡ {title.strip()}")
        return await update.message.reply_text("⚠️ Format: kod;file_id;kino_nomi")

    # Admin xabar yuborish
    if broadcasting.get(user_id):
        broadcasting[user_id] = False
        cursor.execute("SELECT user_id FROM users")
        for (uid,) in cursor.fetchall():
            try:
                await context.bot.send_message(chat_id=int(uid), text=text)
            except:
                continue
        return await update.message.reply_text("✅ Xabar yuborildi!")

    # Admin komandalar
    if user_id in ADMINS:
        if text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            return await update.message.reply_text("📝 Format: kod;file_id;kino_nomi")
        elif text == "📤 Xabar yuborish":
            broadcasting[user_id] = True
            return await update.message.reply_text("✉️ Xabaringizni yozing:")
        elif text == "📊 Statistika":
            user_count = get_user_count()
            movie_count = get_movie_count()
            return await update.message.reply_text(
                f"👥 Foydalanuvchilar: {user_count} ta\n"
                f"🎥 Kinolar: {movie_count} ta"
            )

    # Oddiy foydalanuvchi kino kodi yoki qidiruv
    movie = get_movie(text)
    if movie:
        await update.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        return

    results = search_movies(text)
    if results:
        for m in results:
            await update.message.reply_video(video=m[1], caption=f"🎬 {m[2]}")
    else:
        await update.message.reply_text("❌ Hech narsa topilmadi.")

# === file_id olish ===
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Iltimos, video yuboring.")

# === Inline Qidiruv ===
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return

    results = search_movies(query)
    articles = [
        InlineQueryResultArticle(
            id=m[0],
            title=m[2],
            input_message_content=InputTextMessageContent(
                f"🎬 {m[2]}\n\nKod: {m[0]}"
            ),
            description=f"Kod: {m[0]} | Kategoriya: {m[3]}",
        ) for m in results[:20]
    ]

    await update.inline_query.answer(articles, cache_time=1)

# === Boshlatish ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(InlineQueryHandler(inline_query))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
