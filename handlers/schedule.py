from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, MessageHandler, ContextTypes, filters
from database import SessionLocal, Post, upsert_user
from services.storage import StorageService
from utils.validators import validate_media, normalize_hashtags
from handlers.common import subscription_ok, is_banned
from config import settings

async def begin(update, context, media_type):
    q = update.callback_query
    await q.answer()
    if await is_banned(q.from_user.id):
        await q.message.reply_text("🚫 حسابك متوقف حاليًا.")
        return
    if not await subscription_ok(context.bot, q.from_user.id):
        await q.message.reply_text("📢 اشترك في القنوات المطلوبة الأول يا نجم.")
        return
    context.user_data["flow"] = {"type": media_type}
    await q.message.reply_text(
        "هات الفيديو يا بطل 🎥🔥" if media_type == "video" else "هات الصورة يا نجم 🖼️🔥"
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.data == "schedule_video":
        await begin(update, context, "video")
    elif q.data == "schedule_photo":
        await begin(update, context, "photo")

async def media_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data.get("flow")
    if not flow:
        return
    typ = flow["type"]
    tg_file = update.message.video or update.message.photo[-1]
    if typ == "video":
        tg_obj = update.message.video
        filename = tg_obj.file_name or f"video_{tg_obj.file_unique_id}.mp4"
    else:
        tg_obj = update.message.photo[-1]
        filename = f"photo_{tg_obj.file_unique_id}.jpg"
    f = await tg_obj.get_file()
    data = await f.download_as_bytearray()
    path = StorageService.save_bytes(bytes(data), filename)
    ok, err = validate_media(path, typ)
    if not ok:
        Path(path).unlink(missing_ok=True)
        await update.message.reply_text(f"❌ {err}")
        return
    flow["path"] = path
    flow["telegram_file_id"] = tg_obj.file_id
    flow["stage"] = "caption"
    await update.message.reply_text("✍️ اكتب الكابشن يا نجم:")

async def text_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data.get("flow")
    if not flow:
        return
    stage = flow.get("stage")
    text = update.message.text.strip()
    if stage == "caption":
        flow["caption"] = text
        flow["stage"] = "hashtags"
        await update.message.reply_text("#️⃣ اكتب الهاشتاجات (مثال: #fyp #egypt) أو اكتب - لو مش عايز:")
    elif stage == "hashtags":
        flow["hashtags"] = "" if text == "-" else normalize_hashtags(text)
        flow["stage"] = "date"
        await update.message.reply_text("📅 اكتب التاريخ بالشكل ده: 05/09/2026")
    elif stage == "date":
        try:
            flow["date"] = datetime.strptime(text, "%d/%m/%Y").date()
        except ValueError:
            await update.message.reply_text("التاريخ مش مظبوط 😅\nاكتبه كده: 05/09/2026")
            return
        flow["stage"] = "time"
        await update.message.reply_text("⏰ اكتب الوقت 24 ساعة، مثال: 20:30")
    elif stage == "time":
        try:
            tm = datetime.strptime(text, "%H:%M").time()
        except ValueError:
            await update.message.reply_text("الوقت مش مظبوط 😅 مثال: 20:30")
            return
        dt = datetime.combine(flow["date"], tm)
        from zoneinfo import ZoneInfo
        local = dt.replace(tzinfo=ZoneInfo(settings.timezone))
        flow["scheduled_at"] = local.astimezone(__import__("datetime").timezone.utc).replace(tzinfo=None)
        await preview(update, context)

async def preview(update, context):
    f = context.user_data["flow"]
    caption = f.get("caption", "")
    tags = f.get("hashtags", "")
    await update.message.reply_text(
        "🔥 راجع بيانات المنشور:\n\n"
        f"{'🎥' if f['type']=='video' else '🖼️'} النوع: {f['type']}\n"
        f"✍️ الكابشن: {caption or 'بدون'}\n"
        f"#️⃣ الهاشتاجات: {tags or 'بدون'}\n"
        f"📅 التاريخ: {f['scheduled_at'].strftime('%d/%m/%Y')}\n"
        f"⏰ الوقت: {f['scheduled_at'].strftime('%H:%M')} UTC\n\n"
        "تمام ننفذ الجدولة؟",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ أيوه جدوله", callback_data="confirm_schedule"),
             InlineKeyboardButton("❌ إلغاء", callback_data="cancel_schedule")]
        ])
    )

async def confirm(update, context):
    q = update.callback_query
    await q.answer()
    f = context.user_data.get("flow")
    if not f:
        await q.message.reply_text("مفيش عملية جدولة مفتوحة.")
        return
    if f["scheduled_at"] <= __import__("datetime").datetime.utcnow():
        await q.message.reply_text("⏰ الموعد لازم يكون في المستقبل يا نجم.")
        return
    user = await upsert_user(q.from_user)
    media_url = StorageService.public_url(f["path"]) if f["type"] == "photo" else None
    if f["type"] == "photo" and not media_url:
        await q.message.reply_text(
            "🖼️ الصور محتاجة Public HTTPS URL من دومين متحقق في TikTok Developer.\n"
            "ظبط PUBLIC_BASE_URL وVerified URL Prefix الأول."
        )
        return
    async with SessionLocal() as s:
        p = Post(
            telegram_user_id=q.from_user.id, media_type=f["type"], media_path=f["path"],
            media_url=media_url, telegram_file_id=f.get("telegram_file_id"),
            caption=f.get("caption",""), hashtags=f.get("hashtags",""),
            scheduled_at=f["scheduled_at"], status="pending"
        )
        s.add(p)
        await s.commit()
        pid = p.id
    context.user_data.pop("flow", None)
    await q.message.reply_text(f"تمام يا وحش 💪🔥\nالمنشور #{pid} اتحجز خلاص، وسيبه علينا في المعاد اللي اخترته ⏰.")

async def cancel(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data.pop("flow", None)
    await q.message.reply_text("تمام يا نجم، لغينا العملية 👌")

def register(app):
    app.add_handler(CallbackQueryHandler(buttons, pattern="^(schedule_video|schedule_photo)$"))
    app.add_handler(CallbackQueryHandler(confirm, pattern="^confirm_schedule$"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel_schedule$"))
    app.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO, media_received))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_received))
