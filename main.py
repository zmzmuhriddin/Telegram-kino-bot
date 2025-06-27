import os
import asyncio
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import uvicorn
import nest_asyncio


# === Load environment ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = set(os.getenv("ADMINS", "").split(","))
DATABASE_URL = os.getenv("DATABASE_URL")
RENDER_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
PORT = int(os.getenv("PORT", 10000))


# === Database Connection ===
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()


# === FastAPI App ===
app_web = FastAPI()


# === Telegram Application ===
application = Application.builder().token(BOT_TOKEN).build()


# === Database Tables ===
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    username TEXT,
    last_seen TIMESTAMP
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    username TEXT PRIMARY KEY
);
""")
conn.commit()


# === Functions ===
def add_user(user_id, username):
    cursor.execute(
        "INSERT INTO users (user_id, username, last_seen) VALUES (%s, %s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, last_seen = EXCLUDED.last_seen",
        (user_id, username, datetime.utcnow())
    )
    conn.commit()


def get_movie(code):
    cursor.execute("SELECT * FROM movies WHERE code = %s", (code,))
    return cursor.fetchone()


def search_movies(query):
    cursor.execute("SELECT * FROM movies WHERE title ILIKE %s", (f"%{query}%",))
    return cursor.fetchall()


def get_all_movies():
    cursor.execute("SELECT * FROM movies ORDER BY title")
    return cursor.fetchall()


def get_movies_by_category(category):
    cursor.execute("SELECT * FROM movies WHERE category = %s", (category,))
    return cursor.fetchall()


def get_all_categories():
    cursor.execute("SELECT name FROM categories ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def add_movie(code, file_id, title, category):
    cursor.execute(
        "INSERT INTO movies (code, file_id, title, category) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (code) DO NOTHING",
        (code, file_id, title, category)
    )
    conn.commit()


def delete_movie(code):
    cursor.execute("DELETE FROM movies WHERE code = %s", (code,))
    conn.commit()


def add_category(name):
    cursor.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
    conn.commit()


def delete_category(name):
    cursor.execute("DELETE FROM categories WHERE name = %s", (name,))
    conn.commit()


def get_user_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]


def get_movie_count():
    cursor.execute("SELECT COUNT(*) FROM movies")
    return cursor.fetchone()[0]


def update_movie_views(code):
    cursor.execute("UPDATE movies SET views = views + 1 WHERE code = %s", (code,))
    conn.commit()


def get_top_movies(limit=10):
    cursor.execute("SELECT * FROM movies ORDER BY views DESC LIMIT %s", (limit,))
    return cursor.fetchall()


def get_channels():
    cursor.execute("SELECT username FROM channels")
    return [row[0] for row in cursor.fetchall()]


def add_channel(username):
    cursor.execute(
        "INSERT INTO channels (username) VALUES (%s) ON CONFLICT DO NOTHING",
        (username,)
    )
    conn.commit()


def delete_channel(username):
    cursor.execute("DELETE FROM channels WHERE username = %s", (username,))
    conn.commit()


# === Subscription Check ===
async def check_subscription(user_id, context):
    if str(user_id) in ADMINS:
        return True

    channels = get_channels()
    if not channels:
        return True

    for channel in channels:
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
    channels = get_channels()

    if not channels:
        return await update.message.reply_text("❌ Obuna uchun kanal belgilanmagan.")

    text = "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
    buttons = []

    for channel in channels:
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


# === Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)

    is_sub = await check_subscription(user.id, context)
    if not is_sub:
        return await require_subscription(update, context)

    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n"
        "🎥 Kino ko‘rish uchun kodni yozing yoki kategoriyani tanlang.",
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
        ["➕ Kanal qo‘shish", "🗑 Kanal o‘chirish"],
        ["📤 Xabar yuborish"]
    ]
    await update.message.reply_text(
        "👑 Admin panel:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
        return await update.message.reply_text("🚫 Siz admin emassiz.")

    text = update.message.text

    if text == "📊 Statistika":
        user_count = get_user_count()
        movie_count = get_movie_count()
        await update.message.reply_text(
            f"📊 Statistika:\n\n👥 Foydalanuvchilar: {user_count}\n🎬 Kinolar: {movie_count}"
        )

    elif text == "📥 Top kinolar":
        top = get_top_movies()
        if top:
            msg = "📥 Top kinolar:\n\n"
            for i, m in enumerate(top, 1):
                msg += f"{i}. {m[2]} - {m[4]} marta ko'rilgan\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("Hozircha top kinolar yo‘q.")

    else:
        await update.message.reply_text("❌ Bu tugma hali ishlamaydi. Tez orada qo‘shiladi.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "movies":
        movies = get_all_movies()
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            await query.message.reply_text("🎬 Mavjud kinolar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.reply_text("📭 Hozircha kinolar mavjud emas.")

    elif data == "categories":
        categories = get_all_categories()
        if categories:
            buttons = [[InlineKeyboardButton(c, callback_data=f"category_{c}")] for c in categories]
            await query.message.reply_text("🗂 Kategoriyalar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.reply_text("📭 Kategoriya mavjud emas.")

    elif data.startswith("category_"):
        category = data.split("_", 1)[1]
        movies = get_movies_by_category(category)
        if movies:
            buttons = [[InlineKeyboardButton(m[2], callback_data=f"movie_{m[0]}")] for m in movies]
            await query.message.reply_text(f"🎬 {category} kategoriyasidagi kinolar:", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            await query.message.reply_text(f"📭 {category} kategoriyasida kino yo'q.")

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
            "ℹ️ <b>Ma'lumot:</b>\n\n"
            "Bu bot orqali siz turli kinolarni topishingiz va tomosha qilishingiz mumkin.\n"
            "👨‍💻 Dasturchi: @Zokirov_cinemaxuz\n"
            "📅 Versiya: 3.0",
            parse_mode="HTML"
        )


# === Webhook va ishga tushirish ===
@app_web.get("/")
async def home():
    return {"status": "Bot ishlayapti ✅"}

@app_web.post(f"/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"status": "ok"}

async def setup():
    await application.bot.delete_webhook()
    webhook_url = f"https://{RENDER_HOSTNAME}/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_url)


if __name__ == "__main__":
    nest_asyncio.apply()

    async def main():
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("admin", admin))
        application.add_handler(CallbackQueryHandler(subscription_check_callback, pattern="^check_sub$"))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, admin_panel_handler))

        await application.initialize()
        await setup()
        await application.start()
        print("✅ Bot va webhook ishga tushdi!")

    asyncio.get_event_loop().create_task(main())
    uvicorn.run(app_web, host="0.0.0.0", port=PORT)
