import asyncio
from database import get_post, set_post_status
from services.tiktok_api import TikTokAPI
from telegram import Bot

class Publisher:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.api = TikTokAPI()

    async def publish(self, post_id: int):
        post = await get_post(post_id)
        if not post or post.status != "pending":
            return
        await set_post_status(post_id, "publishing")
        try:
            caption = (post.caption or "") + ((" " + post.hashtags) if post.hashtags else "")
            if post.media_type == "video":
                publish_id = await self.api.direct_video(post.telegram_user_id, post.media_path, caption)
            else:
                if not post.media_url:
                    raise RuntimeError("PHOTO_PUBLIC_URL_MISSING")
                publish_id = await self.api.direct_photo(post.telegram_user_id, post.media_url, caption)

            # TikTok processes posts asynchronously. Do not claim publication until
            # Fetch Status returns PUBLISH_COMPLETE.
            final = None
            for _ in range(72):  # up to ~6 minutes
                final = await self.api.status(post.telegram_user_id, publish_id)
                status = final.get("status")
                if status == "PUBLISH_COMPLETE":
                    await set_post_status(post_id, "published", publish_id=publish_id)
                    await self.bot.send_message(
                        post.telegram_user_id,
                        f"تم يا نجم 🚀🔥\nالمحتوى نزل بنجاح على TikTok.\n\n🆔 Publish ID: {publish_id}"
                    )
                    return
                if status == "FAILED":
                    reason = final.get("fail_reason", "TikTok رفض نشر المحتوى.")
                    raise RuntimeError(reason)
                await asyncio.sleep(5)

            raise RuntimeError("TIKTOK_PROCESSING_TIMEOUT")

        except Exception as exc:
            msg = str(exc)
            await set_post_status(post_id, "failed", error=msg)
            try:
                await self.bot.send_message(
                    post.telegram_user_id,
                    f"يا نجم 😅\nالمنشور رقم #{post_id} مقدرش يتنشر.\n\n"
                    f"السبب:\n{msg}\n\n"
                    "تقدر تجرب تاني من المنشورات الفاشلة."
                )
            except Exception:
                pass
