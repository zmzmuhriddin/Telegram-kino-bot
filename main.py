import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# === Environment ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = set(os.getenv("ADMINS", "").split(","))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
DB_FILE = os.getenv("DB_FILE", "cinemaxuz.db")

# === Database ===
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# === Tables ===
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

# === Functions ===
def add_user(user_id, username):
    with conn:
        conn.execute("REPLACE INTO users VALUES (?, ?, ?)", (user_id, username or "", datetime.utcnow()))

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE):
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

def get_movie(code):
    cursor.execute("SELECT * FROM movies WHERE code=?", (code,))
    return cursor.fetchone()

def search_movies(query):
    cursor.execute("SELECT * FROM movies WHERE title LIKE ?", (f"%{query}%",))
    return cursor.fetchall()

def get_movies_by_category(category):
    cursor.execute("SELECT * FROM movies WHERE category=?", (category,))
    return cursor.fetchall()

def get_all_movies():
    cursor.execute("SELECT * FROM movies")
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

# === States ===
adding_movie = {}
deleting_movie = {}
broadcasting = {}
adding_category = {}
deleting_category = {}

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)

    if not await is_subscribed(user.id, context):
        await update.message.reply_text(f"🚫 Iltimos, {CHANNEL_USERNAME} kanaliga obuna bo‘ling.")
        return

    buttons = [
        [InlineKeyboardButton("🎬 Kinolar", callback_data="movies")],
        [InlineKeyboardButton("🗂 Kategoriyalar", callback_data="categories")],
        [InlineKeyboardButton("🔎 Qidiruv", callback_data="search")],
        [InlineKeyboardButton("ℹ️ Ma'lumot", callback_data="info")]
    ]
    markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        "🎬 CinemaxUZ botiga xush kelibsiz!\n\n"
        "Kino kodini yuboring yoki qidiruvdan foydalaning.",
        reply_markup=markup
    )

# === Buttons ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not await is_subscribed(update.effective_user.id, context):
        await query.message.reply_text(f"🚫 Iltimos, {CHANNEL_USERNAME} kanaliga obuna bo‘ling.")
        return

    if data == "movies":
        movies = get_all_movies()
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            markup = InlineKeyboardMarkup(buttons)
            await query.message.reply_text("🎬 Kinolar:", reply_markup=markup)
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
            await query.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        else:
            await query.message.reply_text("❌ Kino topilmadi.")

    elif data == "search":
        await query.message.reply_text("🔎 Kino nomini yoki kodini yuboring.")

    elif data == "info":
        await query.message.reply_text(
            "ℹ️ CinemaxUZ bot.\n"
            "👨‍💻 Dasturchi: @Zokirov_cinemaxuz\n"
            "👉 Kino kodini yozing yoki qidiruvdan foydalaning."
        )

# === Admin ===
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [
        ["📊 Statistika", "➕ Kino qo‘shish"],
        ["❌ Kino o‘chirish", "🗂 Kategoriya qo‘shish"],
        ["🗑 Kategoriya o‘chirish", "📥 Top kinolar"],
        ["📤 Xabar yuborish"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

# === Text Handler ===
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if not await is_subscribed(update.effective_user.id, context):
        await update.message.reply_text(f"🚫 Iltimos, {CHANNEL_USERNAME} kanaliga obuna bo‘ling.")
        return

    # === Admin commands ===
    if user_id in ADMINS:
        if adding_movie.get(user_id):
            try:
                code, file_id, title, category = map(str.strip, text.split(";"))
                add_movie(code, file_id, title, category)
                adding_movie[user_id] = False
                await update.message.reply_text(f"✅ Qo‘shildi: {title}")
            except:
                await update.message.reply_text("⚠️ Format: kod;file_id;kino_nomi;kategoriya")
            return

        if deleting_movie.get(user_id):
            delete_movie(text)
            deleting_movie[user_id] = False
            await update.message.reply_text(f"❌ O‘chirildi: {text}")
            return

        if adding_category.get(user_id):
            add_category(text)
            adding_category[user_id] = False
            await update.message.reply_text(f"✅ Kategoriya qo‘shildi: {text}")
            return

        if deleting_category.get(user_id):
            delete_category(text)
            deleting_category[user_id] = False
            await update.message.reply_text(f"❌ Kategoriya o‘chirildi: {text}")
            return

        if broadcasting.get(user_id):
            broadcasting[user_id] = False
            cursor.execute("SELECT user_id FROM users")
            for (uid,) in cursor.fetchall():
                try:
                    await context.bot.send_message(chat_id=int(uid), text=text)
                except:
                    continue
            await update.message.reply_text("✅ Xabar yuborildi!")
            return

        if text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            await update.message.reply_text("Format: kod;file_id;kino_nomi;kategoriya")
            return

        if text == "❌ Kino o‘chirish":
            deleting_movie[user_id] = True
            await update.message.reply_text("Kino kodini yuboring.")
            return

        if text == "🗂 Kategoriya qo‘shish":
            adding_category[user_id] = True
            await update.message.reply_text("Kategoriya nomini yuboring.")
            return

        if text == "🗑 Kategoriya o‘chirish":
            deleting_category[user_id] = True
            await update.message.reply_text("Kategoriya nomini yuboring.")
            return

        if text == "📤 Xabar yuborish":
            broadcasting[user_id] = True
            await update.message.reply_text("Xabar matnini yuboring.")
            return

        if text == "📊 Statistika":
            await update.message.reply_text(
                f"👥 Foydalanuvchilar: {get_user_count()}\n"
                f"🎥 Kinolar: {get_movie_count()}\n"
                f"🗂 Kategoriyalar: {len(get_all_categories())}"
            )
            return

        if text == "📥 Top kinolar":
            movies = get_top_movies()
            msg = "🏆 Top kinolar:\n\n"
            for m in movies:
                msg += f"🎬 {m[2]} — {m[4]} ta ko‘rish\n"
            await update.message.reply_text(msg)
            return

    # === Foydalanuvchilar uchun ===
    movie = get_movie(text)
    if movie:
        update_movie_views(movie[0])
        await update.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        return

    results = search_movies(text)
    if results:
        for m in results:
            await update.message.reply_video(video=m[1], caption=f"🎬 {m[2]}")
    else:
        await update.message.reply_text("❌ Hech narsa topilmadi.")

# === Get File ID ===
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Iltimos, video yuboring.")

# === Run ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishga tushdi...")
    app.run_polling()
