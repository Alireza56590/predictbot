import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# تنظیمات ادمین‌ها
ADMINS = {
    262011432: "ادمین اصلی",  # ایدی شما
    # اضافه کردن ادمین‌های دیگر: {ایدی عددی: "نام ادمین"}
}

# دیتابیس ساده (در پروژه واقعی از پایگاه داده استفاده کنید)
DB = {
    "matches": {},
    "teams": {},
    "predictions": {},
    "scores": {},
    "next_match_id": 1
}

# --- دستورات ادمین ---

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن ادمین جدید"""
    if update.effective_user.id != 262011432:
        await update.message.reply_text("❌ فقط ادمین اصلی می‌تواند ادمین اضافه کند")
        return
    
    try:
        new_admin_id = int(context.args[0])
        new_admin_name = " ".join(context.args[1:]) if len(context.args) > 1 else "ادمین جدید"
        ADMINS[new_admin_id] = new_admin_name
        await update.message.reply_text(f"✅ ادمین جدید اضافه شد:\n{new_admin_id} - {new_admin_name}")
    except (IndexError, ValueError):
        await update.message.reply_text("فرمت صحیح:\n/addadmin ایدی_عددی نام_ادمین")

async def add_team(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن تیم جدید"""
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند تیم اضافه کنند")
        return
    
    if not context.args:
        await update.message.reply_text("فرمت صحیح:\n/addteam نام_تیم")
        return
    
    team_name = " ".join(context.args)
    DB["teams"][team_name] = {"players": []}
    await update.message.reply_text(f"✅ تیم '{team_name}' اضافه شد")

async def add_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اضافه کردن بازیکن به تیم"""
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند بازیکن اضافه کنند")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("فرمت صحیح:\n/addplayer نام_تیم نام_بازیکن")
        return
    
    team_name = context.args[0]
    player_name = " ".join(context.args[1:])
    
    if team_name not in DB["teams"]:
        await update.message.reply_text("⚠️ تیم مورد نظر یافت نشد")
        return
    
    DB["teams"][team_name]["players"].append(player_name)
    await update.message.reply_text(f"✅ بازیکن '{player_name}' به تیم '{team_name}' اضافه شد")

async def schedule_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """زمان‌بندی مسابقه جدید"""
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند مسابقه اضافه کنند")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text("فرمت صحیح:\n/addmatch تیم_میزبان تیم_مهمان تاریخ(YYYY-MM-DD) ساعت(HH:MM)")
        return
    
    home_team = context.args[0]
    away_team = context.args[1]
    match_date = context.args[2]
    match_time = context.args[3]
    
    if home_team not in DB["teams"] or away_team not in DB["teams"]:
        await update.message.reply_text("⚠️ یکی از تیم‌ها ثبت نشده است")
        return
    
    match_id = DB["next_match_id"]
    DB["next_match_id"] += 1
    
    DB["matches"][match_id] = {
        "home": home_team,
        "away": away_team,
        "date": match_date,
        "time": match_time,
        "result": None,
        "prediction_deadline": (datetime.strptime(f"{match_date} {match_time}", "%Y-%m-%d %H:%M") - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M")
    }
    
    await update.message.reply_text(
        f"✅ مسابقه با شناسه {match_id} ثبت شد:\n"
        f"🏠 {home_team} vs {away_team} 🏠\n"
        f"📅 تاریخ: {match_date}\n"
        f"⏰ ساعت: {match_time}\n"
        f"⏳ مهلت پیش‌بینی: {DB['matches'][match_id]['prediction_deadline']}"
    )

async def set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت نتیجه نهایی مسابقه"""
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ فقط ادمین‌ها می‌توانند نتیجه را ثبت کنند")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("فرمت صحیح:\n/setresult آیدی_مسابقه نتیجه(home/draw/away)")
        return
    
    try:
        match_id = int(context.args[0])
        result = context.args[1].lower()
        
        if match_id not in DB["matches"]:
            await update.message.reply_text("⚠️ مسابقه مورد نظر یافت نشد")
            return
        
        if result not in ["home", "draw", "away"]:
            await update.message.reply_text("⚠️ نتیجه باید یکی از این موارد باشد: home, draw, away")
            return
        
        DB["matches"][match_id]["result"] = result
        
        # محاسبه امتیازات
        for user_id, prediction in DB["predictions"].get(match_id, {}).items():
            if prediction == result:
                DB["scores"][user_id] = DB["scores"].get(user_id, 0) + 5
            else:
                DB["scores"][user_id] = DB["scores"].get(user_id, 0) + 2
        
        await update.message.reply_text(
            f"✅ نتیجه مسابقه {match_id} ثبت شد:\n"
            f"🏆 نتیجه: {result}\n"
            f"🔢 امتیازات به روزرسانی شدند"
        )
    except ValueError:
        await update.message.reply_text("⚠️ آیدی مسابقه باید عددی باشد")

# --- دستورات کاربران ---

async def show_matches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش مسابقات فعال برای پیش‌بینی"""
    active_matches = []
    now = datetime.now()
    
    for match_id, match in DB["matches"].items():
        if match["result"] is None:
            match_time = datetime.strptime(f"{match['date']} {match['time']}", "%Y-%m-%d %H:%M")
            if now < match_time:
                active_matches.append(
                    f"🆔 {match_id}: {match['home']} vs {match['away']}\n"
                    f"📅 {match['date']} ⏰ {match['time']}\n"
                    f"⏳ مهلت پیش‌بینی: {match['prediction_deadline']}\n"
                )
    
    if not active_matches:
        await update.message.reply_text("⭕ در حال حاضر هیچ مسابقه‌ای برای پیش‌بینی وجود ندارد")
        return
    
    await update.message.reply_text(
        "📌 مسابقات فعال برای پیش‌بینی:\n\n" + 
        "\n".join(active_matches) + 
        "\nبرای پیش‌بینی از دستور /predict آیدی_مسابقه استفاده کنید"
    )

async def predict_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیش‌بینی نتیجه مسابقه"""
    user_id = update.effective_user.id
    
    if not context.args:
        await show_matches(update)
        return
    
    try:
        match_id = int(context.args[0])
        if match_id not in DB["matches"]:
            await update.message.reply_text("⚠️ مسابقه مورد نظر یافت نشد")
            return
        
        match = DB["matches"][match_id]
        now = datetime.now()
        deadline = datetime.strptime(match["prediction_deadline"], "%Y-%m-%d %H:%M")
        
        if now > deadline:
            await update.message.reply_text("⏰ زمان پیش‌بینی برای این مسابقه به پایان رسیده است")
            return
        
        keyboard = [
            [
                InlineKeyboardButton(f"{match['home']} برد", callback_data=f"pred:{match_id}:home"),
                InlineKeyboardButton("مساوی", callback_data=f"pred:{match_id}:draw"),
            ],
            [
                InlineKeyboardButton(f"{match['away']} برد", callback_data=f"pred:{match_id}:away"),
            ]
        ]
        
        await update.message.reply_text(
            f"🔮 پیش‌بینی برای مسابقه {match_id}:\n"
            f"{match['home']} vs {match['away']}\n"
            f"📅 {match['date']} ⏰ {match['time']}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except ValueError:
        await update.message.reply_text("⚠️ آیدی مسابقه باید عددی باشد")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌های پیش‌بینی"""
    query = update.callback_query
    await query.answer()
    
    _, match_id, prediction = query.data.split(":")
    match_id = int(match_id)
    user_id = query.from_user.id
    
    if match_id not in DB["predictions"]:
        DB["predictions"][match_id] = {}
    
    DB["predictions"][match_id][user_id] = prediction
    
    match = DB["matches"][match_id]
    team_names = {
        "home": match["home"],
        "away": match["away"],
        "draw": "مساوی"
    }
    
    await query.edit_message_text(
        f"✅ پیش‌بینی شما ثبت شد:\n"
        f"🆔 مسابقه: {match_id}\n"
        f"⚽ {match['home']} vs {match['away']}\n"
        f"🔮 پیش‌بینی شما: {team_names[prediction]}\n"
        f"⏳ مهلت پیش‌بینی: {match['prediction_deadline']}"
    )

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جدول امتیازات"""
    if not DB["scores"]:
        await update.message.reply_text("🏆 هنوز هیچ امتیازی ثبت نشده است")
        return
    
    sorted_scores = sorted(DB["scores"].items(), key=lambda item: item[1], reverse=True)
    
    leaderboard = ["🏆 جدول امتیازات:\n"]
    for rank, (user_id, score) in enumerate(sorted_scores, start=1):
        try:
            user = await context.bot.get_chat(user_id)
            username = user.username or user.first_name
        except:
            username = f"کاربر {user_id}"
        
        leaderboard.append(f"{rank}. {username}: {score} امتیاز")
    
    await update.message.reply_text("\n".join(leaderboard))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور شروع"""
    user = update.effective_user
    welcome_msg = (
        f"سلام {user.first_name}!\n"
        "🤖 به ربات پیش‌بینی فوتبال خوش آمدید\n\n"
        "🔹 برای مشاهده مسابقات فعال: /matches\n"
        "🔹 برای پیش‌بینی: /predict آیدی_مسابقه\n"
        "🔹 برای مشاهده جدول امتیازات: /leaderboard\n"
    )
    
    if user.id in ADMINS:
        welcome_msg += (
            "\n🔧 دستورات ادمین:\n"
            "🔸 اضافه کردن تیم: /addteam نام_تیم\n"
            "🔸 اضافه کردن بازیکن: /addplayer نام_تیم نام_بازیکن\n"
            "🔸 زمان‌بندی مسابقه: /addmatch تیم_میزبان تیم_مهمان تاریخ ساعت\n"
            "🔸 ثبت نتیجه: /setresult آیدی_مسابقه نتیجه\n"
            "🔸 اضافه کردن ادمین: /addadmin ایدی_عددی نام"
        )
    
    await update.message.reply_text(welcome_msg)

# --- اجرای ربات ---

def main():
    # ساخت اپلیکیشن با نسخه جدید
    app = Application.builder().token(os.environ.get("TELEGRAM_TOKEN")).build()
    
    # دستورات عمومی
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matches", show_matches))
    app.add_handler(CommandHandler("predict", predict_match))
    app.add_handler(CommandHandler("leaderboard", show_leaderboard))
    
    # دستورات ادمین
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("addteam", add_team))
    app.add_handler(CommandHandler("addplayer", add_player))
    app.add_handler(CommandHandler("addmatch", schedule_match))
    app.add_handler(CommandHandler("setresult", set_result))
    
    # هندلر دکمه‌ها
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^pred:"))
    
    # اجرای ربات
    print("🤖 ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
