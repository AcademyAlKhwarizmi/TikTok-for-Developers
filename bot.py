import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, RedirectResponse
import uvicorn

from telegram.ext import Application
from config import settings
from database import init_db
from handlers import register_handlers
from services.oauth import OAuthService
from scheduler import SchedulerService
from utils.logger import logger
from utils.console import print_banner, print_status
from utils.emojis import CUSTOM_IDS

scheduler_service = None
tg_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler_service, tg_app
    await init_db()
    # Restore any Custom Emoji IDs changed from the Admin Panel.
    from database import SessionLocal, Setting
    from sqlalchemy import select
    async with SessionLocal() as s:
        rows = (await s.execute(select(Setting).where(Setting.key.like("emoji:%")))).scalars().all()
        for row in rows:
            key = row.key.split(":", 1)[1]
            if key in CUSTOM_IDS and row.value:
                CUSTOM_IDS[key] = row.value
    tg_app = Application.builder().token(settings.bot_token).build()
    register_handlers(tg_app)
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling(drop_pending_updates=True)

    scheduler_service = SchedulerService(tg_app)
    await scheduler_service.start()

    print_banner()
    print_status(tg_app, scheduler_service)
    logger.info("🚀 FlowTikTok BOT شغال يا وحش!")
    try:
        yield
    finally:
        await scheduler_service.stop()
        await tg_app.updater.stop()
        await tg_app.stop()
        await tg_app.shutdown()

app = FastAPI(title="FlowTikTok OAuth Callback", lifespan=lifespan)

@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "FlowTikTok OK"

@app.get("/oauth/callback")
async def oauth_callback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")
    if error:
        return PlainTextResponse(f"TikTok authorization failed: {error}", status_code=400)
    if not code or not state:
        return PlainTextResponse("Missing OAuth parameters.", status_code=400)
    result = await OAuthService().handle_callback(code, state)
    if not result["ok"]:
        return PlainTextResponse(result["message"], status_code=400)
    return PlainTextResponse("تم ربط TikTok بنجاح. ارجع للبوت يا نجم 🔥")

@app.get("/media/{filename}", name="media")
async def media(filename: str):
    from services.storage import StorageService
    path = StorageService.resolve_filename(filename)
    if not path:
        return PlainTextResponse("Not found", status_code=404)
    from fastapi.responses import FileResponse
    return FileResponse(path)

def run():
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )

if __name__ == "__main__":
    run()
