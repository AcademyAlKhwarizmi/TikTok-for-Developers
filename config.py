import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _csv(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(",") if x.strip()]

@dataclass(frozen=True)
class Settings:
    bot_token: str = os.getenv("BOT_TOKEN", "").split(",")[0].strip()
    admin_id: int = int(os.getenv("ADMIN_ID", "0") or 0)
    developer_username: str = os.getenv("DEVELOPER_USERNAME", "").lstrip("@")
    required_channels: tuple[str, ...] = tuple(_csv(os.getenv("REQUIRED_CHANNELS", "")))

    tiktok_client_key: str = os.getenv("TIKTOK_CLIENT_KEY", "")
    tiktok_client_secret: str = os.getenv("TIKTOK_CLIENT_SECRET", "")
    tiktok_redirect_uri: str = os.getenv("TIKTOK_REDIRECT_URI", "")
    tiktok_scopes: str = os.getenv(
        "TIKTOK_SCOPES", "user.info.basic,video.publish"
    )

    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/flowtiktok.db")
    media_dir: str = os.getenv("MEDIA_DIR", "./media")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    encryption_key: str = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    port: int = int(os.getenv("PORT", "10000") or 10000)
    timezone: str = os.getenv("TIMEZONE", "Africa/Cairo")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_media_mb: int = int(os.getenv("MAX_MEDIA_MB", "512") or 512)

settings = Settings()

if not settings.bot_token:
    raise RuntimeError("BOT_TOKEN is missing.")
if not settings.encryption_key:
    raise RuntimeError("TOKEN_ENCRYPTION_KEY is missing. Generate a Fernet key.")
