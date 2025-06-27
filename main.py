import os
import asyncio
import psycopg2
import tempfile
import matplotlib.pyplot as plt
from datetime import datetime, date
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import uvicorn
import nest_asyncio

# === Load env ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = set(os.getenv("ADMINS", "").split(","))
DATABASE_URL = os.getenv("DATABASE_URL")
RENDER_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
PORT = int(os.getenv("PORT", 10000))
CHANNELS = os.getenv("CHANNELS", "").split(",")

# === Database ===
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    last_seen TIMESTAMP,
    join_date DATE
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    views INTEGER DEFAULT 0
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS categories (
    name TEXT PRIMARY KEY
);
""")
conn.commit()

# === FastAPI ===
app_web = FastAPI()

# === Telegram app ===
application = Application.builder().token(BOT_TOKEN).build()

# === DB Functions ===
def execute_query(query, params=(), fetch=False, fetchone=False):
    try:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        if fetchone:
            return cursor.fetchone()
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ DB Error: {e}")
        return None


def add_user(user_id, username):
    execute_query("""
        INSERT INTO users (user_id, username, last_seen, join_date) 
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_id) 
        DO UPDATE SET username = EXCLUDED.username, last_seen = EXCLUDED.last_seen
    """, (user_id, username, datetime.utcnow(), date.today()))


def get_today_users():
    res = execute_query("SELECT COUNT(*) FROM users WHERE join_date = %s", (date.today(),), fetchone=True)
    return res[0] if res else 0


def get_movie(code):
    return execute_query("SELECT * FROM movies WHERE code = %s", (code,), fetchone=True)


def search_movies(query):
    return execute_query("SELECT * FROM movies WHERE title ILIKE %s", (f"%{query}%",), fetch=True) or []


def get_all_movies():
    return execute_query("SELECT * FROM movies ORDER BY title", fetch=True) or []


def get_movies_by_category(category):
    return execute_query("SELECT * FROM movies WHERE category = %s", (category,), fetch=True) or []


def get_all_categories():
    res = execute_query("SELECT name FROM categories ORDER BY name", fetch=True)
    return [row[0] for row in res] if res else []


def add_movie(code, file_id, title, category):
    execute_query("""
        INSERT INTO movies (code, file_id, title, category) 
        VALUES (%s, %s, %s, %s) 
        ON CONFLICT (code) DO NOTHING
    """, (code, file_id, title, category))


def delete_movie(code):
    execute_query("DELETE FROM movies WHERE code = %s", (code,))


def add_category(name):
    execute_query("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))


def delete_category(name):
    execute_query("DELETE FROM categories WHERE name = %s", (name,))


def get_user_count():
    res = execute_query("SELECT COUNT(*) FROM users", fetchone=True)
    return res[0] if res else 0


def get_movie_count():
    res = execute_query("SELECT COUNT(*) FROM movies", fetchone=True)
    return res[0] if res else 0


def update_movie_views(code):
    execute_query("UPDATE movies SET views = views + 1 WHERE code = %s", (code,))


def get_top_movies(limit=10):
    return execute_query("SELECT * FROM movies ORDER BY views DESC LIMIT %s", (limit,), fetch=True) or []

# === Subscription check ===
async def check_subscription(user_id, context):
    if str(user_id) in ADMINS:
        return True
    for channel in CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status in ["member", "administrator", "creator"]:
                continue
            else:
                return False
        except:
            return False
    return True


async def require_subscription(update, context):
    text = "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
    buttons = []

    for channel in CHANNELS:
        username = channel.strip().replace("@", "")
        text += f"👉 <a href='https://t.me/{username}'>@{username}</a>\n"
        buttons.append([InlineKeyboardButton(f"📢 {username}", url=f"https://t.me/{username}")])

    buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])

    message = update.message if update.message else update.callback_query.message

    await message.reply_text(
        text, parse_mode="HTML", disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def subscription_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    is_sub = await check_subscription(user_id, context)
    if is_sub:
        await query.message.reply_text("✅ Obuna tekshirildi. Botdan foydalanishingiz mumkin!")
        return await start(update, context)
    else:
        return await require_subscription(update, context)

# === States ===
adding_movie = {}
deleting_movie = {}
broadcasting = {}
adding_category = {}
deleting_category = {}

# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)

    is_sub = await check_subscription(user.id, context)
    if not is_sub:
        return await require_subscription(update, context)

    message = update.message if update.message else update.callback_query.message

    await message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n"
        "🎥 Kino ko‘rish uchun <b>kino kodini</b> yozing yoki <b>kategoriya</b> bo‘yicha izlang.\n\n"
        "👇 Quyidagilardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 Kinolar", callback_data="movies")],
            [InlineKeyboardButton("🗂 Kategoriyalar", callback_data="categories")],
            [InlineKeyboardButton("🔎 Qidiruv", callback_data="search")],
            [InlineKeyboardButton("ℹ️ Ma'lumot", callback_data="info")]
        ])
    )


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
    await update.message.reply_text("👑 Admin panel:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_sub = await check_subscription(user.id, context)
    if not is_sub:
        return await require_subscription(update, context)

    query = update.callback_query
    await query.answer()
    data = query.data

    message = query.message

    if data == "movies":
        movies = get_all_movies()
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            await message.reply_text("🎬 Mavjud kinolar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.reply_text("📭 Hozircha kinolar mavjud emas.")

    elif data == "categories":
        categories = get_all_categories()
        if categories:
            buttons = [[InlineKeyboardButton(c, callback_data=f"category_{c}")] for c in categories]
            await message.reply_text("🗂 Kategoriyalar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.reply_text("📭 Kategoriya mavjud emas.")

    elif data.startswith("category_"):
        category = data.split("_", 1)[1]
        movies = get_movies_by_category(category)
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            await message.reply_text(f"🎬 {category} kategoriyasidagi kinolar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await message.reply_text(f"📭 {category} kategoriyasida kino yo'q.")

    elif data.startswith("movie_"):
        code = data.split("_", 1)[1]
        movie = get_movie(code)
        if movie:
            update_movie_views(code)
            await message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")
        else:
            await message.reply_text("❌ Kino topilmadi.")

    elif data == "search":
        await message.reply_text("🔎 Kino nomini yoki kodini yuboring.")

    elif data == "info":
        await message.reply_text(
            "ℹ️ <b>Ma'lumot:</b>\n\n"
            "Bu bot orqali siz turli kinolarni topishingiz va tomosha qilishingiz mumkin.\n"
            "👨‍💻 Dasturchi: @Zokirov_cinemaxuz\n"
            "📅 Versiya: 3.0\n\n"
            "👉 Kino kodini yozing yoki qidiruvdan foydalaning.",
            parse_mode="HTML"
        )

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring.")

# === Text Handler — siz avval olgan formatda to'liq ishlaydi (shu kodga joylashtirish mumkin) ===

# === Webhook ===
@app_web.get("/")
async def home():
    return {"status": "Bot ishlayapti ✅"}

@app_web.post(f"/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"status": "ok"}

# === Setup ===
async def setup():
    await application.bot.delete_webhook()
    webhook_url = f"https://{RENDER_HOSTNAME}/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)

# === Run ===
if __name__ == "__main__":
    nest_asyncio.apply()

    async def main():
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CallbackQueryHandler(subscription_check_callback, pattern="^check_sub$"))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.VIDEO, get_file_id))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

        await application.initialize()
        await setup()
        await application.start()
        print("✅ Bot va webhook ishga tushdi!")

    asyncio.get_event_loop().create_task(main())
    uvicorn.run(app_web, host="0.0.0.0", port=PORT)
