import asyncio
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from database import SessionLocal, Post
from services.publisher import Publisher
from config import settings
from utils.logger import logger

class SchedulerService:
    def __init__(self, tg_app):
        self.app = tg_app
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self.publisher = Publisher(tg_app.bot)

    async def start(self):
        self.scheduler.add_job(self.tick, "interval", seconds=20, id="flowtiktok_tick", replace_existing=True)
        self.scheduler.start()
        await self.tick()

    async def stop(self):
        self.scheduler.shutdown(wait=False)

    async def tick(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        async with SessionLocal() as s:
            posts = (await s.execute(
                select(Post).where(Post.status == "pending", Post.scheduled_at <= now)
            )).scalars().all()
        for p in posts:
            try:
                await self.publisher.publish(p.id)
            except Exception:
                logger.exception("Scheduler publish task crashed for post %s", p.id)
