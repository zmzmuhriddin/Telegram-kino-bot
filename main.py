import os
import asyncio
import psycopg2
import tempfile
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, InputFile
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
    last_seen TIMESTAMP
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


# === Subscription check ===
async def check_subscription(user_id, context):
    if str(user_id) in ADMINS:
        return True
    for channel in CHANNELS:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True


async def require_subscription(update, context, is_callback=False):
    text = "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
    buttons = []

    for channel in CHANNELS:
        username = channel.strip().replace("@", "")
        text += f"👉 <a href='https://t.me/{username}'>@{username}</a>\n"
        buttons.append([InlineKeyboardButton(f"📢 {username}", url=f"https://t.me/{username}")])

    buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check_sub")])

    if is_callback:
        await update.message.reply_text(
            text, parse_mode="HTML", disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.reply_text(
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
        return await require_subscription(query, context, is_callback=True)


# === Database functions ===
def add_user(user_id, username):
    cursor.execute("""
        INSERT INTO users (user_id, username, last_seen) 
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) 
        DO UPDATE SET username = EXCLUDED.username, last_seen = EXCLUDED.last_seen
    """, (user_id, username, datetime.utcnow()))
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
    cursor.execute("""
        INSERT INTO movies (code, file_id, title, category) 
        VALUES (%s, %s, %s, %s) 
        ON CONFLICT (code) DO NOTHING
    """, (code, file_id, title, category))
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

    await update.message.reply_text(
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
        return await require_subscription(update, context, is_callback=True)

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
            "📅 Versiya: 3.0\n\n"
            "👉 Kino kodini yozing yoki qidiruvdan foydalaning.",
            parse_mode="HTML"
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if user_id in ADMINS:
        if adding_movie.get(user_id):
            parts = text.split(";")
            if len(parts) >= 4:
                code, file_id, title, category = map(str.strip, parts)
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

        if text == "📥 Top kinolar":
            movies = get_top_movies()
            message = "🏆 <b>Top 10 ko‘rilgan kinolar:</b>\n\n"
            for m in movies:
                message += f"🎬 {m[2]} — {m[4]} ta ko‘rish\n"
            await update.message.reply_text(message, parse_mode="HTML")
            return

        if text == "📊 Statistika":
            users = get_user_count()
            movies = get_movie_count()
            categories = len(get_all_categories())

            labels = ['Foydalanuvchilar', 'Kinolar', 'Kategoriyalar']
            counts = [users, movies, categories]
            colors = ['#FF6384', '#36A2EB', '#FFCE56']

            plt.figure(figsize=(6, 6))
            plt.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%')
            plt.title("Bot statistikasi")
            plt.tight_layout()

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                plt.savefig(tmpfile.name)
                plt.close()

                await update.message.reply_photo(
                    photo=open(tmpfile.name, 'rb'),
                    caption=f"👥 Foydalanuvchilar: {users}\n"
                            f"🎥 Kinolar: {movies}\n"
                            f"🗂 Kategoriyalar: {categories}"
                )
            os.remove(tmpfile.name)
            return

        if text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            return await update.message.reply_text("📝 Format: kod;file_id;kino_nomi;kategoriya")
        if text == "❌ Kino o‘chirish":
            deleting_movie[user_id] = True
            return await update.message.reply_text("🗑 Kino kodini yuboring.")
        if text == "🗂 Kategoriya qo‘shish":
            adding_category[user_id] = True
            return await update.message.reply_text("➕ Kategoriya nomini yuboring.")
        if text == "🗑 Kategoriya o‘chirish":
            deleting_category[user_id] = True
            return await update.message.reply_text("❌ O‘chiriladigan kategoriya nomini yuboring.")
        if text == "📤 Xabar yuborish":
            broadcasting[user_id] = True
            return await update.message.reply_text("✉️ Xabar matnini yuboring.")

    movie = get_movie(text)
    if movie:
        update_movie_views(text)
        return await update.message.reply_video(video=movie[1], caption=f"🎬 {movie[2]}")

    results = search_movies(text)
    if results:
        for m in results:
            await update.message.reply_video(video=m[1], caption=f"🎬 {m[2]}")
    else:
        await update.message.reply_text("❌ Kino topilmadi.")


async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring.")


# === Web ===
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
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(CallbackQueryHandler(subscription_check_callback, pattern="^check_sub$"))
        application.add_handler(MessageHandler(filters.VIDEO, get_file_id))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

        await application.initialize()
        await setup()
        await application.start()
        print("✅ Bot va webhook ishga tushdi!")

    asyncio.get_event_loop().create_task(main())
    uvicorn.run(app_web, host="0.0.0.0", port=PORT)
