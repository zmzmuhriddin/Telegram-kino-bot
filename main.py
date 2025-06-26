# main.py

import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from flask import Flask, request

# === YUKLASH ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = set(os.getenv("ADMINS", "").split(","))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
DATABASE_URL = os.getenv("DATABASE_URL")
PORT = int(os.getenv("PORT", 10000))
RENDER_HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")

# === POSTGRESGA ULANISH ===
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# === FLASK APP ===
app_web = Flask(__name__)

# === TELEGRAM APP ===
application = Application.builder().token(BOT_TOKEN).build()

# === JADVALLAR ===
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

# === FUNKSIYALAR ===
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

# === HOLATLAR ===
adding_movie = {}
deleting_movie = {}
broadcasting = {}
adding_category = {}
deleting_category = {}

# === HANDLERLAR (start, admin, tugmalar, matn) ===
# ❗ Bu qismini siz ilgari to‘g‘ri yozgansiz — shu holatda qoladi
# Agar xohlasangiz bu qismni ham qo‘shib yuboraman

# === WEBHOOK ===
@app_web.route('/')
def index():
    return "✅ Bot ishlayapti!"

@app_web.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

# === BOTNI ISHGA TUSHURISH ===
if __name__ == "__main__":
    WEBHOOK_URL = f"https://{RENDER_HOSTNAME}/{BOT_TOKEN}"

    application.bot.delete_webhook()
    application.bot.set_webhook(url=WEBHOOK_URL)

    # HANDLERLARNI QO'SHISH
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🚀 Webhook bilan bot ishga tushdi...")
    app_web.run(host="0.0.0.0", port=PORT)
