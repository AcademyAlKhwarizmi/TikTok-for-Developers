from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ContextTypes
from handlers.common import subscription_ok
from database import upsert_user, SessionLocal, TikTokAccount
from sqlalchemy import select
from services.oauth import OAuthService

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await subscription_ok(context.bot, q.from_user.id):
        await q.message.reply_text("اشترك الأول يا بطل.")
        return
    await upsert_user(q.from_user)
    try:
        url = await OAuthService().authorization_url(q.from_user.id)
        await q.message.reply_text(
            "🔗 دوس الزرار ده واربط حساب TikTok بتاعك رسمي من TikTok نفسه.\n\n"
            "مهم: لازم تطبيق TikTok بتاعك يكون واخد الصلاحيات المطلوبة.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎵 ربط TikTok", url=url)],
                [InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")]
            ])
        )
    except Exception as e:
        await q.message.reply_text(f"حصلت مشكلة في تجهيز الربط: {e}")

async def disconnect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = await upsert_user(q.from_user)
    async with SessionLocal() as s:
        account = (await s.execute(select(TikTokAccount).where(TikTokAccount.user_id == user.id))).scalar_one_or_none()
        if account:
            await s.delete(account)
            await s.commit()
    await q.message.reply_text("فصلنا حساب TikTok يا نجم 🔓")

def register(app):
    app.add_handler(CallbackQueryHandler(connect, pattern="^connect_tiktok$"))
    app.add_handler(CallbackQueryHandler(disconnect, pattern="^disconnect_tiktok$"))
