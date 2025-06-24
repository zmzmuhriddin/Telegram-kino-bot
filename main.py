from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
        await update.message.reply_text(f"📎 File ID: {file_id}")
    else:
        await update.message.reply_text("Bu video emas. Video yuboring.")

async def main():
    from os import getenv
    app = ApplicationBuilder().token(getenv("BOT_TOKEN")).build()
    app.add_handler(MessageHandler(filters.VIDEO, get_file_id))
    print("✅ Bot file ID olish uchun tayyor.")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
