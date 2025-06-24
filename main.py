import os import nest_asyncio from dotenv import load_dotenv from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes )

nest_asyncio.apply() load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") ADMIN_ID = os.getenv("ADMIN_ID")

Kod -> (Sarlavha, file_id)

MOVIES = { "1": ("Gladio", "VIDEO_FILE_ID_1"), "2": ("Titanik", "VIDEO_FILE_ID_2") }

Adminlar uchun holat flagi

adding_movie = {}

/start komandasi

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "🎬 <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n🎥 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:", parse_mode="HTML" ) buttons = [[InlineKeyboardButton(f"{code} - {data[0]}", callback_data=code)] for code, data in MOVIES.items()] markup = InlineKeyboardMarkup(buttons) await update.message.reply_text("🎬 Mavjud kinolar:", reply_markup=markup)

Tugma bosilganda

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() code = query.data data = MOVIES.get(code) if data: title, file_id = data await query.message.reply_video(video=file_id, caption=f"🎬 {title}") else: await query.message.reply_text("❌ Kino topilmadi.")

/admin komandasi

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE): if str(update.effective_user.id) != ADMIN_ID: await update.message.reply_text("🚫 Siz admin emassiz.") return

keyboard = [["📊 Statistika", "➕ Kino qo‘shish"], ["📤 Xabar yuborish"]]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
await update.message.reply_text("👑 Admin panelga xush kelibsiz!", reply_markup=reply_markup)

Yagona matn handler — admin yoki user

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) text = update.message.text.strip()

# Admin kino qo‘shish rejimida bo‘lsa
if adding_movie.get(user_id):
    parts = text.split(";", 2)
    if len(parts) == 3:
        code = parts[0].strip()
        title = parts[1].strip()
        file_id = parts[2].strip()
        MOVIES[code] = (title, file_id)
        adding_movie[user_id] = False
        await update.message.reply_text(f"✅ Qo‘shildi: {code} → {title}")
    else:
        await update.message.reply_text(
            "⚠️ Noto‘g‘ri format. Quyidagicha yozing:\n<code>KOD;Sarlavha;file_id</code>",
            parse_mode="HTML"
        )
    return

# Admin panel tugmalari
if user_id == ADMIN_ID:
    if text == "📊 Statistika":
        await update.message.reply_text("👥 Obunachilar soni: 100+")
        return
    elif text == "➕ Kino qo‘shish":
        adding_movie[user_id] = True
        await update.message.reply_text(
            "📝 Quyidagicha yuboring:\n<code>KOD;Sarlavha;file_id</code>", parse_mode="HTML"
        )
        return
    elif text == "📤 Xabar yuborish":
        await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
        return

# Oddiy foydalanuvchi kino kodi kiritganda
data = MOVIES.get(text)
if data:
    title, file_id = data
    await update.message.reply_video(video=file_id, caption=f"🎬 {title}")
else:
    await update.message.reply_text("❌ Bunday kodli kino topilmadi.")

file_id olish uchun

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.video: file_id = update.message.video.file_id await update.message.reply_text(f"🎬 Video file_id:\n<code>{file_id}</code>", parse_mode="HTML") else: await update.message.reply_text("❌ Video yuboring.")

Botni ishga tushirish

if name == 'main': app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("✅ Bot ishga tushdi...")
app.run_polling()

