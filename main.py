from telegram.ext import CommandHandler
import os

ADMIN_ID = int(os.getenv("ADMIN_ID"))

# /stats komandasi – foydalanuvchi sonini ko‘rsatadi
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Siz admin emassiz.")
    
    # Bu yerda siz foydalanuvchilar ro‘yxatini fayl yoki bazadan o‘qishingiz mumkin
    # Masalan, file.txt faylida barchaning ID'lari bo‘lsa:
    try:
        with open("users.txt", "r") as f:
            users = f.readlines()
        count = len(set(users))
    except FileNotFoundError:
        count = 0
    
    await update.message.reply_text(f"📊 Umumiy foydalanuvchilar: {count} ta")

# /sendall komandasi – hamma foydalanuvchilarga xabar yuboradi
async def sendall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ Siz admin emassiz.")

    if not context.args:
        return await update.message.reply_text("ℹ️ Xabar yozing: /sendall Salom!")

    text = " ".join(context.args)
    try:
        with open("users.txt", "r") as f:
            users = set(f.readlines())
    except FileNotFoundError:
        return await update.message.reply_text("🚫 Foydalanuvchilar topilmadi.")

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=int(user_id.strip()), text=text)
        except Exception as e:
            print(f"Xatolik: {e}")

    await update.message.reply_text("✅ Xabar yuborildi.")
