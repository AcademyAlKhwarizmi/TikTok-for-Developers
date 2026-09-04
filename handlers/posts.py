from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ContextTypes
from database import user_posts, SessionLocal, Post, set_post_status
from sqlalchemy import select

LABEL = {
    "pending": "🟡 مستني النشر",
    "publishing": "🔵 بيتنفذ",
    "published": "🟢 اتنشر",
    "failed": "🔴 فشل",
    "cancelled": "⚪ اتلغى",
}

async def show_posts(update, context, scheduled_only=False):
    q = update.callback_query
    await q.answer()
    posts = await user_posts(q.from_user.id, 0, 10)
    if scheduled_only:
        posts = [p for p in posts if p.status == "pending"]
    if not posts:
        await q.message.reply_text("📋 مفيش منشورات هنا لسه يا نجم.")
        return
    lines = ["📋 منشوراتك:\n"]
    rows = []
    for p in posts:
        icon = "🎥" if p.media_type == "video" else "🖼️"
        lines.append(f"{icon} #{p.id} — {p.scheduled_at.strftime('%d/%m/%Y %H:%M')} UTC\n{LABEL.get(p.status,p.status)}")
        if p.status == "pending":
            rows.append([InlineKeyboardButton(f"🗑️ إلغاء #{p.id}", callback_data=f"cancel_post:{p.id}")])
        if p.status == "failed":
            rows.append([InlineKeyboardButton(f"🔄 حاول تاني #{p.id}", callback_data=f"retry_post:{p.id}")])
    await q.message.reply_text("\n\n".join(lines), reply_markup=InlineKeyboardMarkup(rows) if rows else None)

async def cancel_post(update, context):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":")[1])
    p = await __import__("database").get_post(pid)
    if not p or p.telegram_user_id != q.from_user.id or p.status != "pending":
        await q.message.reply_text("المنشور مش متاح للإلغاء.")
        return
    await set_post_status(pid, "cancelled")
    await q.message.reply_text(f"🗑️ تمام، المنشور #{pid} اتلغى.")

async def retry_post(update, context):
    q = update.callback_query
    await q.answer()
    pid = int(q.data.split(":")[1])
    p = await __import__("database").get_post(pid)
    if not p or p.telegram_user_id != q.from_user.id or p.status != "failed":
        await q.message.reply_text("المنشور مش متاح لإعادة المحاولة.")
        return
    await set_post_status(pid, "pending", error=None)
    await q.message.reply_text(f"🔄 رجعنا المنشور #{pid} للـQueue يا بطل.")

async def stats_user(update, context):
    q = update.callback_query
    from sqlalchemy import func
    async with SessionLocal() as s:
        total = (await s.execute(select(func.count(Post.id)).where(Post.telegram_user_id == q.from_user.id))).scalar_one()
        ok = (await s.execute(select(func.count(Post.id)).where(Post.telegram_user_id == q.from_user.id, Post.status == "published"))).scalar_one()
        failed = (await s.execute(select(func.count(Post.id)).where(Post.telegram_user_id == q.from_user.id, Post.status == "failed"))).scalar_one()
    await q.message.reply_text(f"📊 إحصائياتك\n\n📋 كل المنشورات: {total}\n🟢 الناجح: {ok}\n❌ الفاشل: {failed}")

def register(app):
    app.add_handler(CallbackQueryHandler(lambda u,c: show_posts(u,c,False), pattern="^my_posts$"))
    app.add_handler(CallbackQueryHandler(lambda u,c: show_posts(u,c,True), pattern="^scheduled_posts$"))
    app.add_handler(CallbackQueryHandler(cancel_post, pattern=r"^cancel_post:\d+$"))
    app.add_handler(CallbackQueryHandler(retry_post, pattern=r"^retry_post:\d+$"))
