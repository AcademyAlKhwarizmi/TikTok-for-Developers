from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import upsert_user, get_required_channels, get_user

async def ensure_user(update):
    return await upsert_user(update.effective_user)

async def is_banned(tg_id):
    u=await get_user(tg_id)
    return bool(u and u.is_banned)

async def subscription_ok(bot,user_id):
    from database import get_setting
    if (await get_setting("mandatory_subscription","1"))!="1": return True
    for ch in await get_required_channels():
        try:
            member=await bot.get_chat_member(ch.chat_id,user_id)
            if member.status in ("left","kicked"): return False
        except Exception: return False
    return True

async def subscription_keyboard():
    channels=await get_required_channels()
    rows=[[InlineKeyboardButton(f"📢 اشترك في {c.title}",url=c.invite_url)] for c in channels]
    rows.append([InlineKeyboardButton("✅ تأكيد الاشتراك",callback_data="check_subscription")])
    return InlineKeyboardMarkup(rows)
