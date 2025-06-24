import os import sqlite3 import nest_asyncio from dotenv import load_dotenv from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes )

nest_asyncio.apply() load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") ADMINS = os.getenv("ADMINS", "").split(",") USERS_FILE = "users.txt" DB_FILE = "cinemaxuz.db"

--- SQLite setup ---

def get_db_connection(): return sqlite3.connect(DB_FILE)

def setup_db(): conn = get_db_connection() cursor = conn.cursor() cursor.execute(""" CREATE TABLE IF NOT EXISTS movies ( code TEXT PRIMARY KEY, file_id TEXT NOT NULL, title TEXT NOT NULL ) """) conn.commit() conn.close()

--- Database functions ---

def add_movie(code, file_id, title): conn = get_db_connection() cursor = conn.cursor() cursor.execute("INSERT OR REPLACE INTO movies (code, file_id, title) VALUES (?, ?, ?)", (code, file_id, title)) conn.commit() conn.close()

def get_movie(code): conn = get_db_connection() cursor = conn.cursor() cursor.execute("SELECT file_id, title FROM movies WHERE code = ?", (code,)) result = cursor.fetchone() conn.close() return {"file_id": result[0], "title": result[1]} if result else None

def get_all_movies(): conn = get_db_connection() cursor = conn.cursor() cursor.execute("SELECT code, title FROM movies") rows = cursor.fetchall() conn.close() return rows

--- Users ---

def add_user(user_id): if not os.path.exists(USERS_FILE): open(USERS_FILE, "w").close() with open(USERS_FILE, "r") as f: users = f.read().splitlines() if str(user_id) not in users: with open(USERS_FILE, "a") as f: f.write(str(user_id) + "\n")

--- Bot flags ---

adding_movie = {} waiting_broadcast = {}

--- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) add_user(user_id)

await update.message.reply_text(
    "\U0001F3AC <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n\U0001F3A5 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>.",
    parse_mode="HTML"
)

movies = get_all_movies()
if movies:
    buttons = [[InlineKeyboardButton(title, callback_data=code)] for code, title in movies]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("\U0001F3AC Mavjud kinolar:", reply_markup=markup)
else:
    await update.message.reply_text("\U0001F3AC Hozircha kino mavjud emas.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() code = query.data movie = get_movie(code) if movie: await query.message.reply_video(video=movie["file_id"], caption=f"\U0001F3AC {movie['title']}") else: await query.message.reply_text("❌ Kino topilmadi.")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) if user_id not in ADMINS: await update.message.reply_text("🚫 Siz admin emassiz.") return

keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) text = update.message.text.strip()

if adding_movie.get(user_id):
    parts = text.split(";")
    if len(parts) == 3:
        code, file_id, title = parts
        add_movie(code.strip(), file_id.strip(), title.strip())
        adding_movie[user_id] = False
        await update.message.reply_text(f"✅ Qo‘shildi: {code.strip()} ➡ {title.strip()}")
    else:
        await update.message.reply_text("⚠️ Format noto‘g‘ri. To‘g‘ri format: <code>1;file_id;Gladio</code>", parse_mode="HTML")
    return

if waiting_broadcast.get(user_id):
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    for uid in users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=text)
        except:
            continue
    waiting_broadcast[user_id] = False
    await update.message.reply_text("✅ Xabar yuborildi!")
    return

if user_id in ADMINS:
    if text == "📊 Statistika":
        with open(USERS_FILE, "r") as f:
            users = f.read().splitlines()
        await update.message.reply_text(f"👥 Obunachilar soni: {len(users)} ta")
    elif text == "➕ Kino qo‘shish":
        adding_movie[user_id] = True
        await update.message.reply_text("📝 Format: <code>kod;file_id;kino_nomi</code>", parse_mode="HTML")
    elif text == "📤 Xabar yuborish":
        waiting_broadcast[user_id] = True
        await update.message.reply_text("✉️ Xabaringizni yozing:")
    return

movie = get_movie(text)
if movie:
    await update.message.reply_video(video=movie["file_id"], caption=f"🎬 {movie['title']}")
else:
    await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.video: file_id = update.message.video.file_id await update.message.reply_text(f"🎬 file_id:\n<code>{file_id}</code>", parse_mode="HTML") else: await update.message.reply_text("❌ Video yuboring.")

--- Main ---

if name == 'main': setup_db() app = ApplicationBuilder().token(BOT_TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("admin", admin)) app.add_handler(CallbackQueryHandler(button_handler)) app.add_handler(MessageHandler(filters.VIDEO, get_file_id)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)) print("✅ Bot ishga tushdi...") app.run_polling()

