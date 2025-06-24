import os
import nest_asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

nest_asyncio.apply()
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

MOVIES = {
    "1": {"file_id": "VIDEO_FILE_ID_1", "title": "Avatar 2"},
    "2": {"file_id": "VIDEO_FILE_ID_2", "title": "John Wick 4"}
}

adding_movie = {}
broadcast_mode = {}
users_file = "users.txt"

# Yangi foydalanuvchini ro'yxatga olish
def save_user(user_id):
    try:
        if not os.path.exists(users_file):
            with open(users_file, "w") as f:
                f.write("")
        with open(users_file, "r+") as f:
            ids = f.read().splitlines()
            if str(user_id) not in ids:
                f.write(f"{user_id}\n")
    except Exception as e:
        print(f"Foydalanuvchini saqlashda xatolik: {e}")

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    await update.message.reply_text(
        "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:",
        parse_mode="HTML"
    )
    buttons = [[InlineKeyboardButton(movie["title"], callback_data=code)] for code, movie in MOVIES.items()]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)

# Tugma bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data
    movie = MOVIES.get(code)
    if movie:
        await query.message.reply_video(video=movie["file_id"], caption=f"🎬 {movie['title']}")
    else:
        await query.message.reply_text("❌ Kino topilmadi.")

# /admin komandasi
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("🚫 Siz admin emassiz.")
        return
    keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=reply_markup)

# Matnli xabarlar uchun handler
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    # Broadcast holati
    if broadcast_mode.get(user_id):
        broadcast_mode[user_id] = False
        try:
            with open(users_file, "r") as f:
                ids = f.read().splitlines()
                for uid in ids:
                    try:
                        await context.bot.send_message(chat_id=uid, text=text)
                    except:
                        continue
            await update.message.reply_text("✅ Xabar yuborildi.")
        except:
            await update.message.reply_text("⚠️ Xabar yuborishda xatolik.")
        return

    # Kino qo‘shish holati
    if adding_movie.get(user_id):
        parts = text.split(";")
        if len(parts) == 3:
            code, file_id, title = parts
            MOVIES[code.strip()] = {
                "file_id": file_id.strip(),
                "title": title.strip()
            }
            adding_movie[user_id] = False
            await update.message.reply_text(f"✅ Kino qo‘shildi: {code.strip()} ➡ {title.strip()}")
        else:
            await update.message.reply_text(
                "⚠️ Format noto‘g‘ri. To‘g‘ri format: <code>1;file_id;Gladio</code>",
                parse_mode="HTML"
            )
        return

    # Admin tugmalar
    if user_id == ADMIN_ID:
        if text == "📊 Statistika":
            count = 0
            if os.path.exists(users_file):
                with open(users_file, "r") as f:
                    count = len(f.read().splitlines())
            await update.message.reply_text(f"👥 Obunachilar soni: {count}")
            return
        elif text == "➕ Kino qo‘shish":
            adding_movie[user_id] = True
            await update.message.reply_text(
                "📝 Format: <code>kod;file_id;kino_nomi</code>\nMisol: <code>1;BAACAgIA...;Gladio</code>",
                parse_mode="HTML"
            )
            return
        elif text == "📤 Xabar yuborish":
            broadcast_mode[user_id] = True
            await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
            return

    # Foydalanuvchi kino kodi kiritdi
    movie = MOVIES.get(text)
    if movie:
        await update.message.reply_video(video=movie["file_id"], caption=f"🎬 {movie['title']}")
    else:
        await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

# file_id olish uchun
async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"🎬 Video file_id:\n<code>{file_id}</code>", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Video yuboring.")

# Botni ishga tushirish
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("✅ Bot ishga tushdi...")
    app.run_polling()
