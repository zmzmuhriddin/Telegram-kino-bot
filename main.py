from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes from telegram.constants import ParseMode import os from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Masalan: 123456789

Kinolar (video fayl ID yoki havolani qo'yasiz)

MOVIES = { "Avatar 2": "https://example.com/video1.mp4", "John Wick 4": "https://example.com/video2.mp4" }

/start komandasi

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user

await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text="✅ Obuna bo‘ldingiz!\n🎬 Mana sizga birinchi kino:"
)
await context.bot.send_video(
    chat_id=update.effective_chat.id,
    video=MOVIES["Avatar 2"],
    caption="🎬 Avatar 2"
)

# Kino tugmalari
buttons = [
    [InlineKeyboardButton(text=title, callback_data=title)]
    for title in MOVIES
]
reply_markup = InlineKeyboardMarkup(buttons)
await context.bot.send_message(
    chat_id=update.effective_chat.id,
    text="Yana kino tanlang 👇",
    reply_markup=reply_markup
)

Tugma bosilganda ishlaydi

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() title = query.data video_id = MOVIES.get(title) if video_id: await query.message.reply_video(video=video_id, caption=f"🎬 {title}") else: await query.message.reply_text("Kino topilmadi.")

Faqat admin uchun /stats komandasi

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE): if update.effective_user.id != ADMIN_ID: return await update.message.reply_text("⛔ Siz admin emassiz.") await update.message.reply_text("👑 Statistika: foydalanuvchilar soni noma'lum (demo versiya).")

Botni ishga tushurish

async def main(): app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("stats", stats))

print("✅ Bot ishga tushdi...")
await app.run_polling()

if name == "main": import asyncio asyncio.run(main())

