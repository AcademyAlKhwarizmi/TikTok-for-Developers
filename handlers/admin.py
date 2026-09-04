from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import settings
from database import stats, all_users, save_required_channel, get_required_channels, set_setting, get_setting, SessionLocal, User, Post
from sqlalchemy import select
from utils.emojis import CUSTOM_IDS, CATALOG, ce, set_custom_id

def admin_only(user_id):
    return bool(settings.admin_id and user_id == settings.admin_id)

def panel():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="adm_stats"), InlineKeyboardButton("👥 المستخدمين", callback_data="adm_users")],
        [InlineKeyboardButton("📢 القنوات المطلوبة", callback_data="adm_channels"), InlineKeyboardButton("📋 المنشورات", callback_data="adm_posts")],
        [InlineKeyboardButton("🎬 فيديو الشرح", callback_data="adm_tutorial"), InlineKeyboardButton("🎨 الإيموجيات", callback_data="adm_emojis")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"), InlineKeyboardButton("🔧 حالة النظام", callback_data="adm_system")],
        [InlineKeyboardButton("🔄 اشتراك إجباري", callback_data="adm_sub_toggle"), InlineKeyboardButton("🚫 الحظر", callback_data="adm_ban_help")],
    ])

async def admin(update, context):
    if not admin_only(update.effective_user.id):
        await update.effective_message.reply_text("🚫 اللوحة دي للأدمن بس."); return
    await update.effective_message.reply_text(f"{ce('admin')} <b>FlowTikTok Admin Panel</b>\n\nاختار الإدارة المطلوبة:",
                                               reply_markup=panel(), parse_mode="HTML")

async def callbacks(update, context):
    q=update.callback_query; await q.answer()
    if not admin_only(q.from_user.id): await q.message.reply_text("🚫 مش مسموح."); return
    if q.data=="adm_stats":
        total,active,banned,posts,tt=await stats()
        await q.message.reply_text(
            f"{ce('stats')} <b>إحصائيات البوت</b>\n\n👥 إجمالي: <b>{total}</b>\n🟢 نشطين اليوم: <b>{active}</b>\n"
            f"🚫 محظورين: <b>{banned}</b>\n⏳ انتظار: <b>{posts['pending']}</b>\n🔄 تنفيذ: <b>{posts['publishing']}</b>\n"
            f"✅ ناجحة: <b>{posts['published']}</b>\n❌ فاشلة: <b>{posts['failed']}</b>\n🎵 حسابات TikTok: <b>{tt}</b>",
            reply_markup=panel(), parse_mode="HTML")
    elif q.data=="adm_users":
        users=await all_users()
        await q.message.reply_text(f"{ce('user')} <b>المستخدمون</b>\n\nغير المحظورين: <b>{len(users)}</b>\n\n/ban USER_ID\n/unban USER_ID",
                                   reply_markup=panel(), parse_mode="HTML")
    elif q.data=="adm_sub_toggle":
        current=(await get_setting("mandatory_subscription","1"))=="1"; await set_setting("mandatory_subscription","0" if current else "1")
        await q.message.reply_text("🔴 الاشتراك الإجباري اتقفل." if current else "🟢 الاشتراك الإجباري اتفتح.",reply_markup=panel())
    elif q.data=="adm_ban_help":
        await q.message.reply_text("🚫 <b>الحظر</b>\n\n/ban USER_ID\n/unban USER_ID",reply_markup=panel(),parse_mode="HTML")
    elif q.data=="adm_channels":
        ch=await get_required_channels()
        txt=f"{ce('channel')} <b>القنوات المطلوبة</b>\n\n"+("\n".join(f"• {x.title} — <code>{x.chat_id}</code>" for x in ch) if ch else "مفيش قنوات مضافة.")
        txt+="\n\nإضافة: /addchannel chat_id | اسم القناة | رابط الاشتراك"
        await q.message.reply_text(txt,reply_markup=panel(),parse_mode="HTML")
    elif q.data=="adm_posts":
        async with SessionLocal() as s: rows=(await s.execute(select(Post).order_by(Post.id.desc()).limit(20))).scalars().all()
        txt=f"{ce('posts')} <b>آخر المنشورات</b>\n\n"+("\n".join(f"#{p.id} — {p.media_type} — {p.status}" for p in rows) or "مفيش منشورات.")
        await q.message.reply_text(txt,reply_markup=panel(),parse_mode="HTML")
    elif q.data=="adm_system":
        await q.message.reply_text("🔧 <b>حالة النظام</b>\n\n🟢 Telegram\n🟢 Database\n🟢 Scheduler\n🟢 Storage\n🟡 TikTok API حسب اعتماد التطبيق",
                                   reply_markup=panel(),parse_mode="HTML")
    elif q.data=="adm_broadcast":
        context.user_data["admin_broadcast"]=True
        await q.message.reply_text("📢 <b>Broadcast</b>\n\nابعت الرسالة النصية الآن، وسأعرض Preview قبل الإرسال.",parse_mode="HTML")
    elif q.data=="adm_tutorial":
        context.user_data["admin_tutorial"]=True
        await q.message.reply_text("🎬 <b>فيديو الشرح</b>\n\nأرسل فيديو الشرح الآن ليتم حفظ Telegram File ID تلقائيًا.\nأو استخدم /cleartutorial للحذف.",
                                   parse_mode="HTML",reply_markup=panel())
    elif q.data=="adm_emojis":
        text=f"{ce('settings')} <b>Custom Emoji IDs</b>\n\n"+ "\n".join(f"• <code>{k}</code> = <code>{v}</code>" for k,v in CUSTOM_IDS.items())
        text+="\n\nتغيير: /setemoji KEY EMOJI_ID"
        await q.message.reply_text(text,reply_markup=panel(),parse_mode="HTML")

async def addchannel(update, context):
    if not admin_only(update.effective_user.id): return
    parts=[x.strip() for x in update.message.text.partition(" ")[2].split("|")]
    if len(parts)!=3: await update.message.reply_text("الصيغة: /addchannel chat_id | اسم القناة | رابط الاشتراك"); return
    await save_required_channel(parts[0],parts[1],parts[2],True); await update.message.reply_text("✅ القناة اتضافت.")

async def setemoji_cmd(update, context):
    if not admin_only(update.effective_user.id): return
    parts=update.message.text.split()
    if len(parts)!=3 or parts[1] not in CUSTOM_IDS:
        await update.message.reply_text("الصيغة: /setemoji KEY EMOJI_ID"); return
    if not parts[2].isdigit(): await update.message.reply_text("الـEmoji ID لازم يكون رقم."); return
    set_custom_id(parts[1],parts[2]); await set_setting(f"emoji:{parts[1]}",parts[2]); await update.message.reply_text(f"✅ تم تحديث {parts[1]}.")

async def cleartutorial(update, context):
    if admin_only(update.effective_user.id):
        await set_setting("tutorial_video_id",""); await update.message.reply_text("🗑️ تم حذف فيديو الشرح.")

async def admin_tutorial_video(update, context):
    if not admin_only(update.effective_user.id) or not context.user_data.get("admin_tutorial"): return
    if not update.message.video: return
    await set_setting("tutorial_video_id",update.message.video.file_id)
    context.user_data["admin_tutorial"]=False
    await update.message.reply_text("✅ تم حفظ فيديو الشرح.")

async def broadcast_message(update, context):
    if not admin_only(update.effective_user.id) or not context.user_data.get("admin_broadcast"): return
    context.user_data["admin_broadcast"]=False; context.user_data["broadcast_text"]=update.message.text
    await update.message.reply_text(f"⚠️ <b>Preview</b>\n\n{update.message.text}\n\nمتأكد؟",parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ إرسال",callback_data="broadcast_confirm"),InlineKeyboardButton("❌ إلغاء",callback_data="broadcast_cancel")]]))

async def broadcast_confirm(update, context):
    q=update.callback_query; await q.answer()
    if not admin_only(q.from_user.id): return
    text=context.user_data.pop("broadcast_text","")
    if not text: await q.message.reply_text("مفيش رسالة."); return
    sent=failed=0
    for u in await all_users():
        try: await context.bot.send_message(u.telegram_id,text); sent+=1
        except Exception: failed+=1
    await q.message.reply_text(f"📢 البث خلص.\n\n✅ وصل: {sent}\n❌ فشل: {failed}",reply_markup=panel())

async def broadcast_cancel(update, context):
    q=update.callback_query; await q.answer()
    context.user_data.pop("broadcast_text",None); context.user_data.pop("admin_broadcast",None)
    await q.message.reply_text("❌ ألغينا العملية.",reply_markup=panel())

async def ban(update, context):
    if not admin_only(update.effective_user.id): return
    try: uid=int(update.message.text.split()[1])
    except Exception: await update.message.reply_text("الصيغة: /ban USER_ID"); return
    async with SessionLocal() as s:
        user=(await s.execute(select(User).where(User.telegram_id==uid))).scalar_one_or_none()
        if not user: await update.message.reply_text("المستخدم مش موجود."); return
        user.is_banned=True; await s.commit()
    await update.message.reply_text(f"🚫 المستخدم {uid} اتعمله حظر.")

async def unban(update, context):
    if not admin_only(update.effective_user.id): return
    try: uid=int(update.message.text.split()[1])
    except Exception: await update.message.reply_text("الصيغة: /unban USER_ID"); return
    async with SessionLocal() as s:
        user=(await s.execute(select(User).where(User.telegram_id==uid))).scalar_one_or_none()
        if not user: await update.message.reply_text("المستخدم مش موجود."); return
        user.is_banned=False; await s.commit()
    await update.message.reply_text(f"✅ المستخدم {uid} اتفك حظره.")

def register(app):
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CommandHandler("addchannel",addchannel))
    app.add_handler(CommandHandler("ban",ban)); app.add_handler(CommandHandler("unban",unban))
    app.add_handler(CommandHandler("setemoji",setemoji_cmd)); app.add_handler(CommandHandler("cleartutorial",cleartutorial))
    app.add_handler(CallbackQueryHandler(callbacks,pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(broadcast_confirm,pattern="^broadcast_confirm$"))
    app.add_handler(CallbackQueryHandler(broadcast_cancel,pattern="^broadcast_cancel$"))
    app.add_handler(MessageHandler(filters.VIDEO,admin_tutorial_video,group=10))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,broadcast_message,group=10))
