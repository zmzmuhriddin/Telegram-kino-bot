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

# === Tayyorlov ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = set(os.getenv("ADMINS", "").split(","))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Masalan, '@kanal_nomi'
DB_FILE = os.getenv("DB_FILE", "cinemaxuz.db")

# === Bazaga ulanish ===
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# === Jadval yaratish ===
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    title TEXT,
    category TEXT,
    views INTEGER DEFAULT 0
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY
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

def add_user(user_id, username):
    with conn:
        conn.execute("REPLACE INTO users VALUES (?, ?, ?)", (user_id, username or "", datetime.utcnow()))

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """
    Kanalga obuna tekshiruvi (async)
    """
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False

def add_movie(code, file_id, title, category="Yangi"):
    with conn:
        conn.execute("REPLACE INTO movies VALUES (?, ?, ?, ?, 0)", (code, file_id, title, category))

def delete_movie(code):
    with conn:
        conn.execute("DELETE FROM movies WHERE code=?", (code,))

def update_movie(code, file_id=None, title=None, category=None):
    set_clauses = []
    params = []
    if file_id is not None:
        set_clauses.append("file_id=?")
        params.append(file_id)
    if title is not None:
        set_clauses.append("title=?")
        params.append(title)
    if category is not None:
        set_clauses.append("category=?")
        params.append(category)
    if not set_clauses:
        return
    params.append(code)
    with conn:
        conn.execute(f"UPDATE movies SET {', '.join(set_clauses)} WHERE code=?", params)

def get_movie(code):
    cursor.execute("SELECT * FROM movies WHERE code=?", (code,))
    return cursor.fetchone()

def search_movies(query):
    cursor.execute("SELECT * FROM movies WHERE title LIKE ?", (f"%{query}%",))
    return cursor.fetchall()

def get_movies_by_category(category):
    cursor.execute("SELECT * FROM movies WHERE category=?", (category,))
    return cursor.fetchall()

def get_all_categories():
    cursor.execute("SELECT name FROM categories ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def add_category(name):
    with conn:
        conn.execute("INSERT OR IGNORE INTO categories VALUES (?)", (name,))

def delete_category(name):
    with conn:
        conn.execute("DELETE FROM categories WHERE name=?", (name,))

def get_user_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

def get_movie_count():
    cursor.execute("SELECT COUNT(*) FROM movies")
    return cursor.fetchone()[0]

def get_top_movies(limit=10):
    cursor.execute("SELECT * FROM movies ORDER BY views DESC LIMIT ?", (limit,))
    return cursor.fetchall()

def update_movie_views(code):
    with conn:
        conn.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))

# === Holatlar ===
adding_movie = {}
deleting_movie = {}
broadcasting = {}
adding_category = {}
deleting_category = {}

# === /start komanda ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)

    if not await is_subscribed(user.id, context):
        await update.message.reply_text(
            f"🚫 Siz botdan foydalanish uchun {CHANNEL_USERNAME} kanaliga obuna bo‘ling."
        )
        return

    buttons = [
        [InlineKeyboardButton("🎬 Kinolar", callback_data="movies")],
        [InlineKeyboardButton("🗂 Kategoriyalar", callback_data="categories")],
        [InlineKeyboardButton("🔎 Qidiruv", callback_data="search")],
        [InlineKeyboardButton("ℹ️ Ma'lumot", callback_data="info")]
    ]
    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n"
        "🎥 Kino ko‘rish uchun <b>kino kodini</b> yozing yoki <b>kategoriya bo‘yicha</b> izlang.\n\n"
        "Quyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=markup
    )

# === Tugmalar uchun handler ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "movies":
        movies = get_all_movies()
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)
        else:
            await query.message.reply_text("📭 Hozircha kinolar mavjud emas.")

    elif data == "categories":
        categories = get_all_categories()
        if categories:
            buttons = [[InlineKeyboardButton(c, callback_data=f"category_{c}")] for c in categories]
            markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text("🗂 Kategoriyalar:", reply_markup=markup)
        else:
            await query.message.reply_text("📭 Kategoriyalar mavjud emas.")

    elif data.startswith("category_"):
        category = data.split("_", 1)[1]
        movies = get_movies_by_category(category)
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text(f"🎬 {category} kategoriyasidagi kinolar:", reply_markup=markup)
        else:
            await query.message.reply_text(f"📭 {category} kategoriyasida kinolar topilmadi.")

    elif data.startswith("movie_"):
        code = data.split("_", 1)[1]
        movie = get_movie(code)
        if movie:
            update_movie_views(code)
            await update.callback_query.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        else:
            await update.callback_query.message.reply_text("❌ Kino topilmadi.")

    elif data == "search":
        await query.message.reply_text("🔎 Kino nomi yoki kodini yozing.")

    elif data == "info":
        await query.message.reply_text(
            "ℹ️ <b>Ma'lumot:</b>\n\n"
            "Bu bot orqali siz turli kinolarni topishingiz va tomosha qilishingiz mumkin.\n"
            "👨‍💻 Dasturchi: @Zokirov_cinemaxuz\n"
            "📅 Versiya: 1.0\n\n"
            "👉 Kino kodini yozing yoki qidiruvdan foydalaning.",
            parse_mode="HTML"
        )

# === Admin panel ===
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
        return await update.message.reply_text("🚫 Siz admin emassiz.")
    keyboard = [
        ["📊 Statistika", "➕ Kino qo‘shish"],
        ["❌ Kino o‘chirish", "🗂 Kategoriya qo‘shish"],
        ["🗑 Kategoriya o‘chirish", "📥 Top kinolar"],
        ["📤 Xabar yuborish"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

# === Matn bilan ishlash ===
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Obuna tekshiruvi
    if not await is_subscribed(update.effective_user.id, context):
        return await update.message.reply_text(f"🚫 Iltimos, {CHANNEL_USERNAME} kanaliga obuna bo‘ling.")

    # Admin holatlar
    if user_id in ADMINS:
        if adding_movie.get(user_id):
            parts = text.split(";")
            if len(parts) >= 4:
                code, file_id, title, category = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                add_movie(code, file_id, title, category)
                adding_movie[user_id] = False
                return await update.message.reply_text(f"✅ Qo‘shildi: {code} ➡ {title} ({category})")
            else:
                return await update.message.reply_text("⚠️ Format: kod;file_id;kino_nomi;kategoriya")

        if deleting_movie.get(user_id):
            delete_movie(text)
            deleting_movie[user_id] = False
            return await update.message.reply_text(f"❌ O‘chirildi: {text}")

        if adding_category.get(user_id):
            add_category(text)
            adding_category[user_id] = False
            return await update.message.reply_text(f"✅ Kategoriya qo‘shildi: {text}")

        if deleting_category.get(user_id):
            delete_category(text)
            deleting_category[user_id] = False
            return await update.message.reply_text(f"❌ Kategoriya o‘chirildi: {text}")

        if broadcasting.get(user_id):
            broadcasting[user_id] = False
            cursor.execute("SELECT user_id FROM users")
            for (uid,) in cursor.fetchall():
                try:
                    await context.bot.send_message(chat_id=int(uid), text=text)
                except:
                    continue
            return await update.message.reply_text("✅ Xabar yuborildi!")

        # Admin buyruqlari
        if text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            return await update.message.reply_text("📝 Format: kod;file_id;kino_nomi;kategoriya")
        elif text == "❌ Kino o‘chirish":
            deleting_movie[user_id] = True
            return await update.message.reply_text("🗑 Kino kodini yuboring.")
        elif text == "🗂 Kategoriya qo‘shish":
            adding_category[user_id] = True
            return await update.message.reply_text("➕ Kategoriya nomini yuboring.")
        elif text == "🗑 Kategoriya o‘chirish":
            deleting_category[user_id] = True
            return await update.message.reply_text("❌ O‘chiriladigan kategoriya nomini yuboring.")
        elif text == "📤 Xabar yuborish":
            broadcasting[user_id] = True
            return await update.message.reply_text("✉️ Xabar matnini yuboring.")
        elif text == "📥 Top kinolar":
            movies = get_top_movies()
            message = "🏆 <b>Top 10 ko‘rilgan kinolar:</b>\n\n"
            for m in movies:
                message += f"🎬 {m[2]} — {m[4]} ta ko‘rish\n"
            await update.message.reply_text(message, parse_mode="HTML")
            return
        elif text == "📊 Statistika":
            user_count = get_user_count()
            movie_count = get_movie_count()
            category_count = len(get_all_categories())
            await update.message.reply_text(
                f"👥 Foydalanuvchilar: {user_count} ta\n"
                f"🎥 Kinolar: {movie_count} ta\n"
                f"🗂 Kategoriyalar: {category_count} ta"
            )
            return

    # Foydalanuvchi uchun kino kodi yoki nomi bo‘yicha qidiruv
    movie = get_movie(text)
    if movie:
        update_movie_views(text)
        await update.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        return

    results = search_movies(text)
    if results:
        for m in results:
            await update.message.reply_video(video=m[1], caption=f"🎬 {m[2]}")
    else:
        await update.message.reply_text("❌ Hech narsa topilmadi.")

# === file_id olish uchun handler ===
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Iltimos, video yuboring.")

# === Bot ishga tushirish ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
