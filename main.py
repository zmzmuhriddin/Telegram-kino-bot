import os
import json
import sqlite3
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, InlineQueryHandler, filters, ContextTypes
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = os.getenv("ADMINS", "").split(",")
DB_FILE = "cinemaxuz.db"

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

def get_movies_by_category(category):
    cursor.execute("SELECT * FROM movies WHERE category=?", (category,))
    return cursor.fetchall()

def add_user(user_id, username):
    cursor.execute("REPLACE INTO users VALUES (?, ?, ?)", (user_id, username or "", datetime.now()))
    conn.commit()

def get_user_count():
    cursor.execute("SELECT COUNT(*) FROM users")
    return cursor.fetchone()[0]

adding_movie = {}
broadcasting = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(str(user.id), user.username)
    await update.message.reply_text("馃幀 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n馃帴 Kino ko鈥榬ish uchun <b>kino kodini</b> yozing yoki <b>kino nomidan</b> izlang:", parse_mode="HTML")
    movies = get_all_movies()
    if movies:
        buttons = [[InlineKeyboardButton(m[2], callback_data=m[0])] for m in movies[:10]]
        markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("馃幀 Mavjud kinolar:", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    movie = get_movie(query.data)
    if movie:
        await query.message.reply_video(video=movie[1], caption=f"馃幀 {movie[2]}")
    else:
        await query.message.reply_text("鉂� Kino topilmadi.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in ADMINS:
        return await update.message.reply_text("馃毇 Siz admin emassiz.")
    keyboard = [["馃搳 Statistika", "鉃� Kino qo鈥榮hish"], ["馃摛 Xabar yuborish"]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("馃憫 Admin panel:", reply_markup=markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if adding_movie.get(user_id):
        parts = text.split(";")
        if len(parts) >= 3:
            code, file_id, title = parts[0], parts[1], ";".join(parts[2:])
            add_movie(code.strip(), file_id.strip(), title.strip())
            adding_movie[user_id] = False
            return await update.message.reply_text(f"鉁� Qo鈥榮hildi: {code} 鉃� {title}")
        return await update.message.reply_text("鈿狅笍 Format: kod;file_id;kino nomi")

    if broadcasting.get(user_id):
        broadcasting[user_id] = False
        cursor.execute("SELECT user_id FROM users")
        for (uid,) in cursor.fetchall():
            try:
                await context.bot.send_message(chat_id=int(uid), text=text)
            except:
                continue
        return await update.message.reply_text("鉁� Yuborildi!")

    if user_id in ADMINS:
        if text == "鉃� Kino qo鈥榮hish":
            adding_movie[user_id] = True
            return await update.message.reply_text("馃摑 Format: kod;file_id;kino nomi")
        elif text == "馃摛 Xabar yuborish":
            broadcasting[user_id] = True
            return await update.message.reply_text("鉁夛笍 Xabaringizni yozing:")
        elif text == "馃搳 Statistika":
            count = get_user_count()
            return await update.message.reply_text(f"馃懃 Foydalanuvchilar soni: {count}")

    movie = get_movie(text)
    if movie:
        await update.message.reply_video(video=movie[1], caption=f"馃幀 {movie[2]}")
        return

    results = search_movies(text)
    if results:
        for m in results:
            await update.message.reply_video(video=m[1], caption=f"馃幀 {m[2]}")
    else:
        await update.message.reply_text("鉂� Hech narsa topilmadi.")

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"馃幀 file_id: <code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("鉂� Video yuboring")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    results = search_movies(query)
    articles = [InlineQueryResultArticle(
        id=m[0],
        title=m[2],
        input_message_content=InputTextMessageContent(f"馃幀 {m[2]}"),
        description=f"Kod: {m[0]}",
        thumb_url="https://via.placeholder.com/150"
    ) for m in results[:10]]
    await update.inline_query.answer(articles, cache_time=1)

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(InlineQueryHandler(inline_query))
    print("鉁� Bot ishga tayyor!")
    app.run_polling()
