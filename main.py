import os import nest_asyncio from dotenv import load_dotenv from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes )

nest_asyncio.apply() load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") ADMIN_ID = os.getenv("ADMIN_ID")

Kino kodi -> (nom, file_id)

MOVIES = { "1": ("Gladio", "VIDEO_FILE_ID_GLADIO"), "2": ("Avatar 2", "VIDEO_FILE_ID_AVATAR") }

Adminlar uchun flag

adding_movie = {}

/start komandasi

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "\U0001F3AC <b>CinemaxUZ botiga xush kelibsiz!</b>\n\n\U0001F3A5 Kino ko‘rish uchun <i>tugmadan tanlang</i> yoki <b>kino kodini yozing</b>:", parse_mode="HTML" ) buttons = [[InlineKeyboardButton(f"{key} - {value[0]}", callback_data=key)] for key, value in MOVIES.items()] markup = InlineKeyboardMarkup(buttons) await update.message.reply_text("\U0001F3AC Mavjud kinolar:", reply_markup=markup)

Tugma bosilganda

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() key = query.data movie = MOVIES.get(key) if movie: caption, file_id = movie await query.message.reply_video(video=file_id, caption=f"\U0001F3AC {caption}") else: await query.message.reply_text("\u274C Kino topilmadi.")

/admin komandasi

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE): if str(update.effective_user.id) != ADMIN_ID: await update.message.reply_text("\u274C Siz admin emassiz.") return

keyboard = [["\U0001F4CA Statistika", "\u2795 Kino qo‘shish"], ["\U0001F4E4 Xabar yuborish"]]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
await update.message.reply_text("\U0001F451 Admin panelga xush kelibsiz!", reply_markup=reply_markup)

Kino kodi bilan yuborish yoki admin qo‘shishi

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = str(update.effective_user.id) text = update.message.text.strip()

# Admin rejimida yangi kino qo‘shish
if adding_movie.get(user_id):
    if text.count(";") == 2:
        key, title, file_id = [part.strip() for part in text.split(";", 2)]
        MOVIES[key] = (title, file_id)
        adding_movie[user_id] = False
        await update.message.reply_text(f"\u2705 Qo‘shildi: {key} → {title}")
    else:
        await update.message.reply_text("⚠️ Format: kod;nom;file_id", parse_mode="HTML")
    return

# Admin tugmalari
if user_id == ADMIN_ID:
    if text == "\U0001F4CA Statistika":
        await update.message.reply_text("\U0001F465 Obunachilar soni: 100+")
        return
    elif text == "\u2795 Kino qo‘shish":
        adding_movie[user_id] = True
        await update.message.reply_text(
            "\U0001F4DD Format: <code>kod;nom;file_id</code>", parse_mode="HTML")
        return
    elif text == "\U0001F4E4 Xabar yuborish":
        await update.message.reply_text("✉️ Yubormoqchi bo‘lgan xabaringizni yozing:")
        return

# Oddiy kino kodi
movie = MOVIES.get(text)
if movie:
    caption, file_id = movie
    await update.message.reply_video(video=file_id, caption=f"\U0001F3AC {caption}")
else:
    await update.message.reply_text("\u274C Bunday kino topilmadi.")

file_id olish uchun

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.message.video: file_id = update.message.video.file_id await update.message.reply_text(f"\U0001F3AC Video file_id:\n<code>{file_id}</code>", parse_mode="HTML") else: await update.message.reply_text("\u274C Video yuboring.")

Ishga tushirish

if name == 'main': app = ApplicationBuilder().token(BOT_TOKEN).build() app.add_handler(CommandHandler("start", start)) app.add_handler(CommandHandler("admin", admin)) app.add_handler(CallbackQueryHandler(button_handler)) app.add_handler(MessageHandler(filters.VIDEO, get_file_id)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("\u2705 Bot ishga tushdi...")
app.run_polling()

