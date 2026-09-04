import pytest
from datetime import datetime, timezone
from database import init_db, SessionLocal, User, Post

@pytest.mark.asyncio
async def test_models_create():
    await init_db()
    async with SessionLocal() as s:
        u = User(telegram_id=999001, username="test")
        s.add(u)
        await s.commit()
        p = Post(telegram_user_id=999001, media_type="video", media_path="/tmp/x.mp4",
                 scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None))
        s.add(p)
        await s.commit()
        assert p.id is not None
