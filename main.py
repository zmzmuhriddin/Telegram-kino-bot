import os
import asyncio
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
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
CHANNELS = os.getenv("CHANNELS", "").split(",")


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
conn.commit()


# === Subscription Check ===
async def check_subscription(user_id, context):
    try:
        for channel in CHANNELS:
            member = await context.bot.get_chat_member(chat_id=channel.strip(), user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except:
        return False


async def require_subscription(update, context):
    text = "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
    buttons = []
    for channel in CHANNELS:
        username = channel.strip().replace("@", "")
        text += f"👉 https://t.me/{username}\n"
        buttons.append([InlineKeyboardButton(f"✅ {username}", url=f"https://t.me/{username}")])
    text += "\nObuna bo‘lgach qayta urinib ko‘ring."

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def require_subscription_callback(query, context):
    text = "❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:\n\n"
    buttons = []
    for channel in CHANNELS:
        username = channel.strip().replace("@", "")
        text += f"👉 https://t.me/{username}\n"
        buttons.append([InlineKeyboardButton(f"✅ {username}", url=f"https://t.me/{username}")])
    text += "\nObuna bo‘lgach qayta urinib ko‘ring."

    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# === Database Functions ===
# ➕ add_user, get_movie, search_movies va boshqalar sizning kodingizda to‘g‘ri ishlaydi.
# (Avvalgi versiyadagi kabi ishlaydi, bu joyni qisqartirdim)

# === States ===
adding_movie = {}
deleting_movie = {}
broadcasting = {}
adding_category = {}
deleting_category = {}


# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_subscribed = await check_subscription(user.id, context)
    if not is_subscribed:
        return await require_subscription(update, context)

    add_user(str(user.id), user.username)
    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n"
        "🎥 Kino ko‘rish uchun <b>kino kodini</b> yozing yoki <b>kategoriya</b> bo‘yicha izlang.\n\n"
        "Quyidagilardan birini tanlang:",
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

    await update.message.reply_text(
        "👑 Admin panel:",
        reply_markup=ReplyKeyboardMarkup([
            ["📊 Statistika", "➕ Kino qo‘shish"],
            ["❌ Kino o‘chirish", "🗂 Kategoriya qo‘shish"],
            ["🗑 Kategoriya o‘chirish", "📥 Top kinolar"],
            ["📤 Xabar yuborish"]
        ], resize_keyboard=True)
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        return await require_subscription_callback(query, context)

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
            "📅 Versiya: 1.0\n\n"
            "👉 Kino kodini yozing yoki qidiruvdan foydalaning.",
            parse_mode="HTML"
        )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        return await require_subscription(update, context)

    text = update.message.text.strip()

    # Admin va kino qidirish funksiyasi shu yerda davom etadi
    # (Avvalgi kodda qanday bo'lsa, to'liq qo'llang)

    # Misol:
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


# === FastAPI Routes ===
@app_web.get("/")
async def home():
    return {"status": "Bot ishlayapti ✅"}

@app_web.post(f"/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, application.bot)
    await application.update_queue.put(update)
    return {"status": "ok"}


# === Webhook Setup ===
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
        application.add_handler(MessageHandler(filters.VIDEO, get_file_id))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

        await application.initialize()
        await setup()
        await application.start()
        print("✅ Bot va webhook ishga tushdi!")

    asyncio.get_event_loop().create_task(main())
    uvicorn.run(app_web, host="0.0.0.0", port=PORT)
