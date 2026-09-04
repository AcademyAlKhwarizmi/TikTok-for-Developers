from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from sqlalchemy import select
from database import upsert_user, SessionLocal, TikTokAccount, get_setting
from handlers.common import subscription_ok, subscription_keyboard
from utils.emojis import ce

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 ربط TikTok", callback_data="connect_tiktok"),
         InlineKeyboardButton("📤 نشر فيديو", callback_data="schedule_video")],
        [InlineKeyboardButton("🖼️ نشر صورة", callback_data="schedule_photo"),
         InlineKeyboardButton("📋 منشوراتي", callback_data="my_posts")],
        [InlineKeyboardButton("⏰ المنشورات المجدولة", callback_data="scheduled_posts")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats"),
         InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
        [InlineKeyboardButton("🎬 شرح استخدام البوت", callback_data="tutorial")],
        [InlineKeyboardButton("💬 الدعم والمساعدة", callback_data="developer_contact")],
    ])

async def show_home(update, context):
    u = await upsert_user(update.effective_user)
    if u.is_banned:
        await update.effective_message.reply_text(
            f"{ce('error')} <b>الحساب متوقف</b>\n\nكلم المطور لو شايف إن الإيقاف بالخطأ.",
            parse_mode="HTML")
        return
    if not await subscription_ok(context.bot, update.effective_user.id):
        await update.effective_message.reply_text(
            f"{ce('channel')} <b>أهلاً بيك في FlowTikTok</b>\n\n"
            "قبل ما نبدأ، اشترك في القنوات المطلوبة ثم اضغط تأكيد.",
            reply_markup=await subscription_keyboard(), parse_mode="HTML")
        return
    async with SessionLocal() as s:
        account = (await s.execute(select(TikTokAccount).where(TikTokAccount.user_id == u.id))).scalar_one_or_none()
    status = f"{ce('success')} TikTok مربوط" if account else f"{ce('error')} TikTok غير مربوط"
    name = update.effective_user.first_name or "يا نجم"
    text = (f"{ce('home')} <b>FlowTikTok</b>\n\n"
            f"أهلاً <b>{name}</b> 👋\n"
            "من هنا تقدر تربط حسابك، ترفع المحتوى، وتحدد موعد النشر بسهولة.\n\n"
            f"{status}\n\nاختار الخدمة اللي محتاجها:")
    await update.effective_message.reply_text(text, reply_markup=main_keyboard(), parse_mode="HTML")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_home(update, context)

async def tutorial(update, context):
    q = update.callback_query
    await q.answer()
    file_id = await get_setting("tutorial_video_id")
    if file_id:
        await context.bot.send_video(
            q.from_user.id, file_id,
            caption="🎬 <b>شرح استخدام FlowTikTok</b>\n\nاتفرج على الفيديو خطوة بخطوة، وبعدها ارجع للقائمة.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")]]))
    else:
        await q.message.reply_text(
            "🎬 <b>شرح الاستخدام</b>\n\n"
            "1️⃣ اربط حساب TikTok.\n2️⃣ اختر نشر فيديو أو صورة.\n"
            "3️⃣ أرسل الملف.\n4️⃣ اكتب الكابشن والهاشتاجات.\n"
            "5️⃣ حدد التاريخ والوقت.\n6️⃣ راجع البيانات واضغط تأكيد.\n\n"
            "فيديو الشرح لم يرفعه الأدمن بعد.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")]]))

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "check_subscription":
        if await subscription_ok(context.bot, q.from_user.id):
            await q.message.edit_text(f"{ce('success')} <b>تمام يا وحش</b>\nاشتراكك تمام، نبدأ؟",
                                      reply_markup=main_keyboard(), parse_mode="HTML")
        else:
            await q.message.edit_text(f"{ce('error')} لسه يا نجم 😅\nاشترك في كل القنوات وبعدين دوس تأكيد.",
                                      reply_markup=await subscription_keyboard(), parse_mode="HTML")
    elif q.data == "start_menu":
        await show_home(update, context)
    elif q.data == "tutorial":
        await tutorial(update, context)
    elif q.data == "developer_contact":
        from config import settings
        text = (f"{ce('support')} <b>الدعم والمطور</b>\n\nتواصل: @{settings.developer_username}"
                if settings.developer_username else "بيانات المطور غير مضبوطة في .env.")
        await q.message.reply_text(text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")]]))
    elif q.data == "settings":
        await q.message.reply_text(
            f"{ce('settings')} <b>الإعدادات</b>\n\nإعدادات النشر الأساسية تظهر أثناء إنشاء المنشور.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="start_menu")]]))
    elif q.data == "my_stats":
        from handlers.posts import stats_user
        await stats_user(update, context)

def register(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks, pattern=r"^(check_subscription|start_menu|developer_contact|settings|my_stats|tutorial)$"))
