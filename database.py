from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, DateTime, Text, Boolean, ForeignKey,
    select, func, update, delete
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config import settings

engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class TikTokAccount(Base):
    __tablename__ = "tiktok_accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    open_id: Mapped[str] = mapped_column(String(255), unique=True)
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[str] = mapped_column(Text)
    access_expires_at: Mapped[datetime] = mapped_column(DateTime)
    refresh_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str] = mapped_column(Text, default="")
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    media_type: Mapped[str] = mapped_column(String(20))
    media_path: Mapped[str] = mapped_column(Text)
    media_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    telegram_file_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caption: Mapped[str] = mapped_column(Text, default="")
    hashtags: Mapped[str] = mapped_column(Text, default="")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    publish_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

class RequiredChannel(Base):
    __tablename__ = "required_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[str] = mapped_column(String(255))
    invite_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")

class AdminLog(Base):
    __tablename__ = "admin_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Broadcast(Base):
    __tablename__ = "broadcasts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str] = mapped_column(Text)
    sent: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Log(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class OAuthState(Base):
    __tablename__ = "oauth_states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    state: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

async def init_db():
    import os
    os.makedirs("./data", exist_ok=True)
    os.makedirs(settings.media_dir, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_user(telegram_id: int, session: AsyncSession | None = None):
    owns = session is None
    session = session or SessionLocal()
    try:
        return (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    finally:
        if owns:
            await session.close()

async def upsert_user(tg_user):
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.telegram_id == tg_user.id))).scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not user:
            user = User(telegram_id=tg_user.id, username=tg_user.username, first_name=tg_user.first_name,
                        created_at=now, last_seen_at=now)
            s.add(user)
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_seen_at = now
        await s.commit()
        return user

async def list_pending_posts():
    async with SessionLocal() as s:
        return (await s.execute(
            select(Post).where(Post.status == "pending").order_by(Post.scheduled_at)
        )).scalars().all()

async def get_post(post_id: int):
    async with SessionLocal() as s:
        return (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()

async def set_post_status(post_id: int, status: str, error: str | None = None, publish_id: str | None = None):
    async with SessionLocal() as s:
        p = (await s.execute(select(Post).where(Post.id == post_id))).scalar_one_or_none()
        if not p:
            return
        p.status = status
        p.error_message = error
        if publish_id:
            p.publish_id = publish_id
        if status == "published":
            p.published_at = datetime.now(timezone.utc)
        if status == "publishing":
            p.attempts += 1
        await s.commit()

async def user_posts(tg_id: int, offset=0, limit=5):
    async with SessionLocal() as s:
        return (await s.execute(
            select(Post).where(Post.telegram_user_id == tg_id)
            .order_by(Post.created_at.desc()).offset(offset).limit(limit)
        )).scalars().all()

async def count(query):
    async with SessionLocal() as s:
        return (await s.execute(query)).scalar_one()

async def stats():
    async with SessionLocal() as s:
        total_users = (await s.execute(select(func.count(User.id)))).scalar_one()
        active = (await s.execute(select(func.count(User.id)).where(User.last_seen_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)))).scalar_one()
        banned = (await s.execute(select(func.count(User.id)).where(User.is_banned == True))).scalar_one()
        posts = {}
        for status in ("pending", "publishing", "published", "failed", "cancelled"):
            posts[status] = (await s.execute(select(func.count(Post.id)).where(Post.status == status))).scalar_one()
        tt = (await s.execute(select(func.count(TikTokAccount.id)))).scalar_one()
        return total_users, active, banned, posts, tt

async def all_users():
    async with SessionLocal() as s:
        return (await s.execute(select(User).where(User.is_banned == False))).scalars().all()

async def save_required_channel(chat_id, title, invite_url, enabled=True):
    async with SessionLocal() as s:
        row = (await s.execute(select(RequiredChannel).where(RequiredChannel.chat_id == chat_id))).scalar_one_or_none()
        if not row:
            row = RequiredChannel(chat_id=str(chat_id), title=title, invite_url=invite_url, enabled=enabled)
            s.add(row)
        else:
            row.title, row.invite_url, row.enabled = title, invite_url, enabled
        await s.commit()

async def get_required_channels():
    async with SessionLocal() as s:
        return (await s.execute(select(RequiredChannel).where(RequiredChannel.enabled == True))).scalars().all()

async def set_setting(key, value):
    async with SessionLocal() as s:
        row = (await s.execute(select(Setting).where(Setting.key == key))).scalar_one_or_none()
        if not row:
            row = Setting(key=key, value=value)
            s.add(row)
        else:
            row.value = value
        await s.commit()

async def get_setting(key, default=None):
    async with SessionLocal() as s:
        row = (await s.execute(select(Setting).where(Setting.key == key))).scalar_one_or_none()
        return row.value if row else default
