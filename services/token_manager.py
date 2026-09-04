from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select
from config import settings
from database import SessionLocal, TikTokAccount
from services.crypto import decrypt, encrypt

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

class TokenManager:
    async def get_access_token(self, user_id: int):
        async with SessionLocal() as s:
            account = (await s.execute(select(TikTokAccount).where(TikTokAccount.user_id == user_id))).scalar_one_or_none()
            if not account:
                raise RuntimeError("TIKTOK_NOT_CONNECTED")
            if account.access_expires_at > datetime.now(timezone.utc) + timedelta(minutes=2):
                return decrypt(account.access_token_enc)
            refresh = decrypt(account.refresh_token_enc)

        data = {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(TOKEN_URL, data=data)
        payload = r.json()
        if r.status_code >= 400 or payload.get("error"):
            raise RuntimeError("TIKTOK_RECONNECT_REQUIRED")
        now = datetime.now(timezone.utc)
        async with SessionLocal() as s:
            account = (await s.execute(select(TikTokAccount).where(TikTokAccount.user_id == user_id))).scalar_one()
            account.access_token_enc = encrypt(payload["access_token"])
            if payload.get("refresh_token"):
                account.refresh_token_enc = encrypt(payload["refresh_token"])
            account.access_expires_at = now + timedelta(seconds=int(payload["expires_in"]))
            if payload.get("refresh_expires_in"):
                account.refresh_expires_at = now + timedelta(seconds=int(payload["refresh_expires_in"]))
            account.scopes = payload.get("scope", account.scopes)
            account.updated_at = now
            await s.commit()
        return payload["access_token"]
