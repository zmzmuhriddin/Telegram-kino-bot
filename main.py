import os import sqlite3 from dotenv import load_dotenv from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes ) from datetime import datetime

Load .env

load_dotenv() BOT_TOKEN = os.getenv("BOT_TOKEN") ADMINS = os.getenv("ADMINS", "").split(",")

SQLite

conn = sqlite3.connect("cinemaxuz.db", check_same_thread=False) cursor = conn.cursor()

cursor.execute(""" CREATE TABLE IF NOT EXISTS movies ( code TEXT PRIMARY KEY, file_id TEXT, title TEXT, category TEXT, description TEXT ) """)

cursor.execute(""" CREATE TABLE IF NOT EXISTS users ( user_id TEXT PRIMARY KEY, username TEXT, last_seen TIMESTAMP ) """) conn.commit()

adding_movie = {} broadcasting = {}

=== Helper functions ===

def add_user(user_id, username): cursor.execute("REPLACE INTO users VALUES (?, ?, ?)", (user_id, username or "", datetime.now())) conn.commit()

def add_movie(code, file_id, title, category, description): cursor.execute("REPLACE INTO movies VALUES (?, ?, ?, ?, ?)", (code, file_id, title, category, description)) conn.commit()

def get_movie(code): cursor.execute("SELECT * FROM movies WHERE code=?", (code,)) return cursor.fetchone()

def get_movies(offset=0, limit=10): cursor.execute("SELECT * FROM movies LIMIT ? OFFSET ?", (limit, offset)) return cursor.fetchall()

def get_movie_count(): cursor.execute("SELECT COUNT(*) FROM movies") return cursor.fetchone()[0]

def search_movies(query): cursor.execute("SELECT * FROM movies WHERE title LIKE ?", (f"%{query}%",)) return cursor.fetchall()

def get_user_count(): cursor.execute("SELECT COUNT(*) FROM users") return cursor.fetchone()[0]

=== Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user add_user(str(user.id), user.username) await update.message.reply_text("🎬 Xush kelibsiz! Kino kodini yozing yoki nomdan izlang.")

movies = get_movies()
if movies:
    buttons = [[InlineKeyboardButton(m[2], callback_data=m[0])] for m in movies]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎥 Mavjud kinolar:", reply_markup=markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() code = query.data movie = get_movie(code) if movie: caption = f"🎬 {movie[2]}\n📂 Kategoriya: {movie[3]}\n📝 {movie[4]}" await query.message.reply_video(video=movie[1], caption=caption) else: await query.message.reply_text("❌ Kino topilmadi.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) if user_id not in ADMINS: return await update.message.reply_text("⛔ Siz admin emassiz.")

keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
await update.message.reply_text("👑 Admin panel:", reply_markup=markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) text = update.message.text.strip()

if adding_movie.get(user_id):
    parts = text.split(";")
    if len(parts) >= 5:
        code, file_id, title, category, description = [p.strip() for p in parts[:5]]
        add_movie(code, file_id, title, category, description)
        adding_movie[user_id] = False
        return await update.message.reply_text(f"✅ Qo‘shildi: {title}")
    return await update.message.reply_text("❗ Format: kod;file_id;nom;kategoriya;tavsif")

if broadcasting.get(user_id):
    broadcasting[user_id] = False
    cursor.execute("SELECT user_id FROM users")
    for (uid,) in cursor.fetchall():
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
        except:
            continue
    return await update.message.reply_text("📤 Yuborildi!")

if user_id in ADMINS:
    if text == "📊 Statistika":
        count = get_user_count()
        return await update.message.reply_text(f"👥 Foydalanuvchilar: {count} ta")
    elif text == "➕ Kino qo‘shish":
        adding_movie[user_id] = True
        return await update.message.reply_text("📥 Format: kod;file_id;nom;kategoriya;tavsif")
    elif text == "📤 Xabar yuborish":
        broadcasting[user_id] = True
        return await update.message.reply_text("✉️ Yuboriladigan xabarni yozing")

movie = get_movie(text)
if movie:
    caption = f"🎬 {movie[2]}\n📂 {movie[3]}\n📝 {movie[4]}"
    await update.message.reply_video(video=movie[1], caption=caption)
    return

results = search_movies(text)
if results:
    for m in results:
        await update.message.reply_video(video=m[1], caption=f"🎬 {m[2]}\n📂 {m[3]}\n📝 {m[4]}")
    return
await update.message.reply_text("❌ Topilmadi.")

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.video: file_id = update.message.video.file_id await update.message.reply_text(f"🎬 file_id: <code>{file_id}</code>", parse_mode="HTML")

=== Run bot ===

if name == 'main': app = ApplicationBuilder().token(BOT_TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("admin", admin)) app.add_handler(CallbackQueryHandler(button_handler)) app.add_handler(MessageHandler(filters.VIDEO, get_file_id)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)) print("🚀 CinemaxUZ bot ishga tushdi!") app.run_polling()

