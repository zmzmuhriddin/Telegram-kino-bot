import os
import psycopg2
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# === Load env ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = set(os.getenv("ADMINS", "").split(","))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL")

# === Connect to PostgreSQL ===
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# === Create tables ===
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
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()

# === Functions ===
def add_user(user_id, username):
    cursor.execute("""
        INSERT INTO users (user_id, username, last_seen)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET username = EXCLUDED.username, last_seen = NOW();
    """, (user_id, username))
    conn.commit()

def is_admin(user_id):
    return str(user_id) in ADMINS

def add_movie(code, file_id, title, category):
    cursor.execute("""
        INSERT INTO movies (code, file_id, title, category, views)
        VALUES (%s, %s, %s, %s, 0)
        ON CONFLICT (code) DO UPDATE SET file_id = EXCLUDED.file_id, title = EXCLUDED.title, category = EXCLUDED.category;
    """, (code, file_id, title, category))
    conn.commit()

def delete_movie(code):
    cursor.execute("DELETE FROM movies WHERE code = %s;", (code,))
    conn.commit()

def get_movie(code):
    cursor.execute("SELECT * FROM movies WHERE code = %s;", (code,))
    return cursor.fetchone()

def search_movies(query):
    cursor.execute("SELECT * FROM movies WHERE title ILIKE %s;", (f"%{query}%",))
    return cursor.fetchall()

def get_top_movies(limit=10):
    cursor.execute("SELECT * FROM movies ORDER BY views DESC LIMIT %s;", (limit,))
    return cursor.fetchall()

def get_stats():
    cursor.execute("SELECT COUNT(*) FROM users;")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies;")
    movies = cursor.fetchone()[0]
    return users, movies

def update_movie_views(code):
    cursor.execute("UPDATE movies SET views = views + 1 WHERE code = %s;", (code,))
    conn.commit()

# === /start ===
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
        "🎬 CinemaxUZ botiga xush kelibsiz!\nKino kodini yuboring yoki qidiruvdan foydalaning.",
        reply_markup=markup
    )

# === Admin ===
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return

    keyboard = [
        ["📊 Statistika", "➕ Kino qo‘shish"],
        ["❌ Kino o‘chirish", "📥 Top kinolar"],
        ["📤 Xabar yuborish", "👥 Users List"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

# === Matn handler ===
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    add_user(user_id, update.effective_user.username)

    # Admin commands
    if is_admin(user_id):
        if text == "➕ Kino qo‘shish":
            await update.message.reply_text("Format: kod;file_id;kino_nomi;kategoriya")
            context.user_data["adding_movie"] = True
            return

        if text == "❌ Kino o‘chirish":
            await update.message.reply_text("Kino kodini yuboring.")
            context.user_data["deleting_movie"] = True
            return

        if text == "📥 Top kinolar":
            top = get_top_movies()
            msg = "🏆 Top kinolar:\n\n"
            for m in top:
                msg += f"🎬 {m[2]} — {m[4]} ta ko‘rish\n"
            await update.message.reply_text(msg)
            return

        if text == "📊 Statistika":
            users, movies = get_stats()
            await update.message.reply_text(f"👥 Foydalanuvchilar: {users}\n🎥 Kinolar: {movies}")
            return

        if text == "👥 Users List":
            cursor.execute("SELECT user_id, username FROM users;")
            users = cursor.fetchall()
            msg = "👥 Foydalanuvchilar ro‘yxati:\n\n"
            for user_id, username in users:
                name = username if username else "Noma'lum"
                msg += f"🆔 {user_id} — @{name}\n"
            await update.message.reply_text(msg)
            return

        if text == "📤 Xabar yuborish":
            await update.message.reply_text("✉️ Xabar matnini yuboring.")
            context.user_data["broadcasting"] = True
            return

        if context.user_data.get("adding_movie"):
            try:
                code, file_id, title, category = map(str.strip, text.split(";"))
                add_movie(code, file_id, title, category)
                await update.message.reply_text(f"✅ Qo‘shildi: {title}")
            except:
                await update.message.reply_text("⚠️ Format xato!")
            context.user_data["adding_movie"] = False
            return

        if context.user_data.get("deleting_movie"):
            delete_movie(text)
            await update.message.reply_text(f"❌ O‘chirildi: {text}")
            context.user_data["deleting_movie"] = False
            return

        if context.user_data.get("broadcasting"):
            cursor.execute("SELECT user_id FROM users;")
            for (uid,) in cursor.fetchall():
                try:
                    await context.bot.send_message(chat_id=int(uid), text=text)
                except:
                    continue
            await update.message.reply_text("✅ Xabar yuborildi!")
            context.user_data["broadcasting"] = False
            return

    # Foydalanuvchi uchun kino qidirish
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

# === Button handler ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "info":
        await query.message.reply_text("ℹ️ CinemaxUZ bot. Dasturchi: @zokirov_cinemaxuz")
    elif data == "search":
        await query.message.reply_text("🔎 Kino nomini yoki kodini yuboring.")
    elif data == "movies":
        cursor.execute("SELECT code, title FROM movies;")
        movies = cursor.fetchall()
        if movies:
            buttons = [[InlineKeyboardButton(m[1], callback_data=f"movie_{m[0]}")] for m in movies]
            await query.message.reply_text("🎬 Kinolar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.reply_text("📭 Kinolar mavjud emas.")
    elif data.startswith("movie_"):
        code = data.split("_", 1)[1]
        movie = get_movie(code)
        if movie:
            update_movie_views(movie[0])
            await query.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        else:
            await query.message.reply_text("❌ Kino topilmadi.")

# === File ID olish ===
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        await update.message.reply_text(f"📥 file_id: {update.message.video.file_id}")

# === Run ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("✅ Bot ishlayapti...")
    app.run_polling()
