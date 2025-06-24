import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNELS = os.getenv("CHANNELS", "").split(",")

async def check_subs(user_id, context):
    for channel in CHANNELS:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await check_subs(user_id, context):
        await update.message.reply_text("✅ Obuna bo‘ldingiz!\n🎬 Mana sizga kino: 🎬 Kino bu yerda...")
    else:
        buttons = [[InlineKeyboardButton(ch, url=f"https://t.me/{ch[1:]}")] for ch in CHANNELS]
        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="check")])
        await update.message.reply_text("❗ Kanal(lar)ga obuna bo‘ling:", reply_markup=InlineKeyboardMarkup(buttons))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await check_subs(query.from_user.id, context):
        await query.edit_message_text("✅ Tekshiruvdan o‘tdingiz!\n🎬 Mana kino: 🎬 Kino bu yerda...")
    else:
        await query.edit_message_text("🚫 Hali obuna emassiz.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("✅ Bot ishga tushdi…")
    app.run_polling()
