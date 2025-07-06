# bot.py

# کتابخانه های مورد نیاز را وارد می‌کنیم
import os
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# آی‌دی مدیر (ایدی عددی تلگرام شما)
ADMINS = [262011432]  # اینجا آی‌دی عددی خودت رو بگذار، مثلا 123456789
# توکن ربات از متغیر محیطی خوانده می‌شود
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# ایجاد/اتصال به دیتابیس SQLite
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

# ساخت جدول ها اگر وجود نداشت
cursor.execute("""CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team TEXT,
    away_team TEXT,
    deadline TEXT,
    result_home INTEGER,
    result_away INTEGER
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    match_id INTEGER,
    predicted_home INTEGER,
    predicted_away INTEGER
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    total_score INTEGER DEFAULT 0
)""")
conn.commit()

# دستور افزودن بازی جدید (فقط توسط مدیر)
async def add_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("شما اجازه این کار را ندارید.")
        return
    try:
        home_team, away_team, deadline = context.args
        cursor.execute("INSERT INTO matches (home_team, away_team, deadline) VALUES (?, ?, ?)",
                       (home_team, away_team, deadline))
        conn.commit()
        await update.message.reply_text("بازی جدید اضافه شد.")
    except:
        await update.message.reply_text("فرمت درست: /add_match نام_تیم_میزبان نام_تیم_میهمان زمان_مهلت")

# دستور ثبت نتیجه (فقط مدیر)
async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("شما اجازه این کار را ندارید.")
        return
    try:
        match_id, result_home, result_away = map(int, context.args)
        cursor.execute("UPDATE matches SET result_home=?, result_away=? WHERE id=?",
                       (result_home, result_away, match_id))
        conn.commit()
        await update.message.reply_text("نتیجه ثبت شد.")
    except:
        await update.message.reply_text("فرمت درست: /set_result آیدی_بازی گل_تیم_میزبان گل_تیم_میهمان")

# دستور پیش‌بینی (کاربر می‌تواند ویرایش هم کند)
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        match_id, predicted_home, predicted_away = map(int, context.args)
        # بررسی وجود پیش‌بینی قبلی
        cursor.execute("SELECT id FROM predictions WHERE user_id=? AND match_id=?",
                       (user_id, match_id))
        result = cursor.fetchone()
        if result:
            cursor.execute("UPDATE predictions SET predicted_home=?, predicted_away=? WHERE id=?",
                           (predicted_home, predicted_away, result[0]))
            await update.message.reply_text("پیش‌بینی شما بروزرسانی شد.")
        else:
            cursor.execute("INSERT INTO predictions (user_id, match_id, predicted_home, predicted_away) VALUES (?, ?, ?, ?)",
                           (user_id, match_id, predicted_home, predicted_away))
            await update.message.reply_text("پیش‌بینی شما ثبت شد.")
        conn.commit()
    except:
        await update.message.reply_text("فرمت درست: /predict آیدی_بازی گل_تیم_میزبان گل_تیم_میهمان")

# دستور دیدن لیست بازی‌ها
async def matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT id, home_team, away_team, deadline FROM matches")
    games = cursor.fetchall()
    if games:
        text = "بازی‌های موجود:\n"
        for g in games:
            text += f"آیدی: {g[0]} | {g[1]} - {g[2]} | مهلت: {g[3]}\n"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("بازی‌ای موجود نیست.")

# اجرای ربات
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("add_match", add_match))
    app.add_handler(CommandHandler("set_result", set_result))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("matches", matches))
    print("ربات روشن شد...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
